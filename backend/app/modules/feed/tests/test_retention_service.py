"""보관 정책 배치: 정상 경로 + 실패/방어 경로. 실행기 없이 함수 단위로 검증한다.

`ARTICLES` 정책은 hard delete다 — 요약을 먼저 버린 뒤 원문을 지운다. 되돌릴 수 없는 삭제라
"몇 건이 지워지는가"와 "무엇이 함께 지워지는가"를 둘 다 확인한다.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import Article, Summary, Translation
from app.modules.feed.services.curation_service import run_curation
from app.modules.feed.services.retention_service import run_retention


def _after_seed_window() -> datetime:
    """시드 기사 발행 시각보다 뒤 시점. 보관 기간 0일과 조합해 전부 만료시킨다."""
    return datetime.now(timezone.utc) + timedelta(days=1)


def test_retention_hard_deletes_articles_with_their_summaries(db, seed):
    """정상: 보관 기간이 지난 원문은 요약을 먼저 버린 뒤 삭제된다.

    translations / feed_items 는 summaries 삭제에 FK CASCADE로 따라간다 —
    보관 배치가 직접 지우지 않는다.
    """
    run_curation(db)
    assert db.query(FeedItem).count() == 1

    result = run_retention(db, article_retention_days=0, now=_after_seed_window())

    # 시드 기사 2건(요약 있는 1건 + 요약 없는 1건), 요약 1건.
    assert result.deleted_articles == 2
    assert result.deleted_summaries == 1
    assert result.dry_run is False

    assert db.query(Article).count() == 0
    assert db.query(Summary).count() == 0
    # CASCADE로 함께 정리된 것들
    assert db.query(Translation).count() == 0
    assert db.query(FeedItem).count() == 0


def test_retention_keeps_articles_within_window(db, seed):
    """정상: 보관 기간 안의 원문은 건드리지 않는다."""
    run_curation(db)

    result = run_retention(db, article_retention_days=365)

    assert result.deleted_articles == 0
    assert result.deleted_summaries == 0
    assert db.query(Article).count() == 2
    assert db.query(Summary).count() == 1
    assert db.query(FeedItem).count() == 1


def test_retention_dry_run_counts_but_does_not_delete(db, seed):
    """되돌릴 수 없는 삭제이므로 dry_run으로 대상 건수를 먼저 확인할 수 있어야 한다."""
    run_curation(db)

    result = run_retention(
        db, article_retention_days=0, dry_run=True, now=_after_seed_window()
    )

    assert result.dry_run is True
    assert result.deleted_articles == 2
    assert result.deleted_summaries == 1
    # 아무것도 지워지지 않았다.
    assert db.query(Article).count() == 2
    assert db.query(Summary).count() == 1
    assert db.query(FeedItem).count() == 1


def test_retention_can_skip_articles(db, seed):
    """원문 보관 기간이 확정되지 않은 환경에서는 피드만 정리할 수 있어야 한다."""
    run_curation(db)

    result = run_retention(
        db, retention_days=0, article_retention_days=None, now=_after_seed_window()
    )

    assert result.deleted_feed_items == 1
    assert result.deleted_articles == 0
    assert result.deleted_summaries == 0
    assert db.query(Article).count() == 2
    assert db.query(Summary).count() == 1


def test_deleting_article_before_its_summary_is_blocked(db, seed):
    """방어 확인: 요약이 남아 있으면 원문 삭제 자체가 실패한다.

    `fk_summaries_article`의 `ON DELETE RESTRICT`가 동작한다는 뜻이고, 보관 배치가
    [삭제 순서]를 지켜야 하는 이유가 이것이다. 순서를 어기면 여기처럼 실패한다.
    """
    with pytest.raises(IntegrityError):
        db.execute(delete(Article).where(Article.id == seed["article"].id))
        db.flush()


def _policy(db, target, days, *, active=True):
    from app.modules.feed.models.retention_policy import RetentionPolicy

    p = RetentionPolicy(
        target_entity=target, retention_days=days, strategy="BATCH_DELETE", is_active=active
    )
    db.add(p)
    db.flush()
    return p


def test_retention_reads_days_from_policy_table(db, seed):
    """보관 일수를 인자로 주지 않으면 정책 테이블 값을 쓴다.

    이게 없으면 관리자 화면에서 기간을 바꿔도 배치가 코드 상수를 계속 써서 반영되지 않는다.
    """
    from app.modules.feed.models.retention_policy import TARGET_ARTICLES, TARGET_FEED_ITEMS

    run_curation(db)
    _policy(db, TARGET_FEED_ITEMS, 90)
    articles_policy = _policy(db, TARGET_ARTICLES, 0)  # 0일 = 전부 만료

    result = run_retention(db, now=_after_seed_window())

    assert result.deleted_articles == 2
    assert articles_policy.last_executed_at is not None  # 실행 시각이 기록된다


def test_inactive_policy_skips_that_target(db, seed):
    """정책을 꺼두면 그 대상은 배치가 건너뛴다.

    화면의 "자동 삭제 켜짐/꺼짐"이 실제로 배치를 멈춰야 의미가 있다.
    """
    from app.modules.feed.models.retention_policy import TARGET_ARTICLES, TARGET_FEED_ITEMS

    run_curation(db)
    _policy(db, TARGET_FEED_ITEMS, 90)
    _policy(db, TARGET_ARTICLES, 0, active=False)  # 만료 기간이지만 꺼져 있다

    result = run_retention(db, now=_after_seed_window())

    assert result.deleted_articles == 0
    assert db.query(Article).count() == 2
