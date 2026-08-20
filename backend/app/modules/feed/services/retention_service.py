"""데이터 보관 정책 로직.

실행기 비의존. 보관 기간은 설정으로 외부화하며 코드에 상수로 박지 않는다.
되돌릴 수 없는 삭제이므로 항상 건수를 반환해 배치 로그로 남긴다.

[ARTICLES 정책 = hard delete]
스키마 V2는 `articles` → `summaries` / `feed_items` FK를 `ON DELETE RESTRICT`로 두었다.
따라서 `DELETE FROM articles`를 그냥 부르면 요약이 남아 있는 한 실패한다. 이건 막힌 게 아니라
의도된 방어다 — 원문은 URL로 재수집할 수 있지만 요약은 LLM을 다시 호출해야 만들어지므로,
보관 배치가 원문을 지우면서 비용을 태워 만든 결과를 조용히 연쇄 삭제하는 것을 스키마가
차단한다 (schema.sql V2 [삭제 순서], CLAUDE.md §8-11).

hard delete는 "요약을 버린다"는 판단을 **명시적으로 먼저 내리는 것**이고, 그래서 순서가 있다.

  1) DELETE summaries  → translations, feed_items 가 FK CASCADE로 함께 정리된다
  2) DELETE articles   → article_tags 가 FK CASCADE로 함께 정리된다

되돌릴 수 없으므로 `dry_run=True`로 대상 건수를 먼저 확인할 수 있게 했고, 실제 삭제 시에도
요약/원문 건수를 각각 반환해 `job_logs`에 남긴다.

[소유권 예외] `read_only.py`의 모델은 원칙적으로 조회 전용이고 `summaries` 쓰기 소유자는 B다
(SKILL §4-2). 보관 정책 배치만 예외다 — 데이터 보관은 CLAUDE.md §3에서 C 담당으로 명시돼
있고, 위 [삭제 순서]대로면 요약 삭제 없이는 원문을 지울 수 없다. **이 파일 밖에서
`summaries`를 지우지 않는다.**
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import Article, Summary
from app.modules.feed.models.retention_policy import (
    TARGET_ARTICLES,
    TARGET_FEED_ITEMS,
    RetentionPolicy,
)

# `retention_policies` 행이 없을 때만 쓰는 최후 기본값. 정상 경로에서는 테이블 값을 읽는다
# (리비전 0004_seed_retention이 기본 정책을 넣는다).
DEFAULT_FEED_ITEM_RETENTION_DAYS = 90
DEFAULT_ARTICLE_RETENTION_DAYS = 365


def _policy(db: Session, target_entity: str) -> RetentionPolicy | None:
    return db.scalar(
        select(RetentionPolicy).where(RetentionPolicy.target_entity == target_entity)
    )


def _days_from_policy(db: Session, target_entity: str, fallback: int) -> int | None:
    """정책 테이블에서 보관 일수를 읽는다.

    - 행이 없으면 fallback (테스트·초기 환경)
    - `is_active`가 꺼져 있으면 None → 그 대상은 이번 실행에서 건너뛴다.
      화면의 "자동 삭제 켜짐/꺼짐"이 실제로 배치를 멈춰야 의미가 있다.
    """
    policy = _policy(db, target_entity)
    if policy is None:
        return fallback
    return policy.retention_days if policy.is_active else None


@dataclass
class RetentionResult:
    feed_item_cutoff: datetime
    article_cutoff: datetime
    deleted_feed_items: int
    # hard delete로 함께 버려진 요약 수. translations / feed_items는 CASCADE로 따라간다.
    deleted_summaries: int
    deleted_articles: int
    dry_run: bool


def run_retention(
    db: Session,
    *,
    retention_days: int | None = None,
    article_retention_days: int | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> RetentionResult:
    """보관 기간이 지난 데이터를 정리한다.

    보관 일수를 인자로 주지 않으면 `retention_policies` 테이블에서 읽는다 — 관리자 화면에서
    바꾼 값이 배치에 실제로 반영되게 하기 위함이다. 인자를 주면 그 값이 우선한다(테스트·수동 실행).

    정책의 `is_active`가 꺼져 있으면 그 대상은 건너뛴다.
    """
    now = now or datetime.now(timezone.utc)
    if retention_days is None:
        retention_days = _days_from_policy(db, TARGET_FEED_ITEMS, DEFAULT_FEED_ITEM_RETENTION_DAYS)
    if article_retention_days is None:
        article_retention_days = _days_from_policy(
            db, TARGET_ARTICLES, DEFAULT_ARTICLE_RETENTION_DAYS
        )
    # 정책이 꺼져 있으면(None) 피드 정리를 건너뛴다. cutoff는 로그 형태 유지를 위해 now로 둔다.
    feed_item_cutoff = now - timedelta(days=retention_days) if retention_days is not None else now
    deleted_feed_items = (
        _purge_feed_items(db, cutoff=feed_item_cutoff, dry_run=dry_run)
        if retention_days is not None
        else 0
    )

    if article_retention_days is None:
        # 원문을 건드리지 않을 때도 cutoff 자리는 채워 둔다 — 로그 형태를 갈라놓지 않기 위함.
        if not dry_run and retention_days is not None:
            _mark_executed(db, [TARGET_FEED_ITEMS], now)
        return RetentionResult(
            feed_item_cutoff=feed_item_cutoff,
            article_cutoff=feed_item_cutoff,
            deleted_feed_items=deleted_feed_items,
            deleted_summaries=0,
            deleted_articles=0,
            dry_run=dry_run,
        )

    article_cutoff = now - timedelta(days=article_retention_days)
    deleted_summaries, deleted_articles = _purge_articles(
        db, cutoff=article_cutoff, dry_run=dry_run
    )

    if not dry_run:
        _mark_executed(db, [TARGET_FEED_ITEMS, TARGET_ARTICLES], now)

    return RetentionResult(
        feed_item_cutoff=feed_item_cutoff,
        article_cutoff=article_cutoff,
        deleted_feed_items=deleted_feed_items,
        deleted_summaries=deleted_summaries,
        deleted_articles=deleted_articles,
        dry_run=dry_run,
    )


def _mark_executed(db: Session, target_entities: list[str], now: datetime) -> None:
    """실행 시각을 정책에 남긴다. 관리자 화면의 "마지막 실행"이 이 값이다."""
    for target in target_entities:
        policy = _policy(db, target)
        if policy is not None:
            policy.last_executed_at = now
    db.flush()


def _purge_feed_items(db: Session, *, cutoff: datetime, dry_run: bool) -> int:
    """보관 기간이 지난 개인화 피드 행을 지운다.

    원문·요약은 건드리지 않는다. 피드는 `curate.py`가 언제든 다시 만들 수 있으므로
    여기서 지우는 것은 되돌릴 수 있는 삭제다.
    """
    target_ids = list(db.scalars(select(FeedItem.id).where(FeedItem.created_at < cutoff)))
    if dry_run or not target_ids:
        return len(target_ids)

    db.execute(delete(FeedItem).where(FeedItem.id.in_(target_ids)))
    db.flush()
    return len(target_ids)


def _purge_articles(db: Session, *, cutoff: datetime, dry_run: bool) -> tuple[int, int]:
    """보관 기간이 지난 원문을 hard delete 한다. (요약 건수, 원문 건수) 반환.

    **되돌릴 수 없다.** 요약은 LLM 재호출 없이 복구되지 않는다. 모듈 docstring의 [삭제 순서]를
    지켜야 하며, 순서를 바꾸면 `fk_summaries_article`의 RESTRICT에 걸려 실패한다.
    """
    article_ids = list(db.scalars(select(Article.id).where(Article.published_at < cutoff)))
    if not article_ids:
        return 0, 0

    summary_ids = list(db.scalars(select(Summary.id).where(Summary.article_id.in_(article_ids))))
    if dry_run:
        return len(summary_ids), len(article_ids)

    # 1) 요약을 먼저 버린다. translations / feed_items 는 FK CASCADE 로 따라 지워진다.
    if summary_ids:
        db.execute(delete(Summary).where(Summary.id.in_(summary_ids)))
    # 2) 원문 삭제. article_tags 는 FK CASCADE.
    #    여기서 RESTRICT 오류가 나면 1)이 놓친 참조가 있다는 뜻이므로 삼키지 않고 그대로 올린다.
    db.execute(delete(Article).where(Article.id.in_(article_ids)))
    db.flush()
    # CASCADE로 지워진 행이 세션 캐시에 남아 있으면 이후 조회가 어긋난다.
    db.expire_all()
    return len(summary_ids), len(article_ids)
