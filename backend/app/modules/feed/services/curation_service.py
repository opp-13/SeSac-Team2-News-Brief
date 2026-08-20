"""콘텐츠 큐레이션 로직 (feed_items 생성).

실행기 비의존: 스케줄러/큐 데코레이터를 붙이지 않는다. 인자를 받아 결과를 반환하는 함수만 둔다.
`feed_items` INSERT는 C 전용이다. summaries/translations는 읽기만 한다.
"""

from dataclasses import dataclass

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models.user import User  # 같은 담당(C) 소유 모듈이므로 참조 허용
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import Article, ArticleTag, Summary, Translation
from app.modules.feed.models.tag import UserTag

# 태그 매칭은 `article_tags` 매핑으로 한다 (schema.sql V2 §2, "큐레이션 매칭 기준").
#
# 이전에는 기사 **제목 부분일치**로 매칭했다. 그 방식은 두 가지로 틀렸다.
#   1. 오매칭 — "AI"가 "AIDS"에, "개발"이 "개발도상국"에 걸린다.
#   2. 미매칭 — 실제 데이터에서 대부분의 태그가 제목에 아예 안 나온다. 시드 기준으로
#      "반도체"·"경제"·"정치" 등 9개 태그 전부 제목매칭 0건인데 article_tags에는 매핑이
#      있었다. 그래서 관심 태그를 고른 신규 사용자의 피드가 **한 건도 만들어지지 않았다.**
ARTICLE_STATUS_READY = "SUMMARIZED"  # articles.status ENUM (schema.sql V2)


@dataclass
class FeedSyncResult:
    """관심 태그 변경 후 피드를 맞춘 결과."""

    created: int
    deleted: int
    repointed: int


@dataclass
class CurationResult:
    scanned_users: int
    created_items: int
    skipped_no_summary: int
    skipped_duplicate: int


def curate_for_user(db: Session, *, user: User, article_limit: int = 200) -> tuple[int, int, int]:
    """한 사용자의 관심 태그에 맞는 기사로 feed_items를 만든다. (생성, 요약없음, 중복) 반환."""
    tag_ids = set(db.scalars(select(UserTag.tag_id).where(UserTag.user_id == user.id)))
    if not tag_ids:
        return 0, 0, 0

    # 관심 태그가 붙은 기사만 후보로 뽑고, **어느 태그 때문에 뽑혔는지**를 함께 가져온다.
    # 그 값이 feed_items.matched_tag_id(노출 사유)가 된다 — 이전처럼 관심 태그 목록의
    # 첫 번째를 무조건 박으면 사유가 기사와 무관해진다.
    rows = db.execute(
        select(Article, ArticleTag.tag_id)
        .join(ArticleTag, ArticleTag.article_id == Article.id)
        .where(Article.status == ARTICLE_STATUS_READY, ArticleTag.tag_id.in_(tag_ids))
        .order_by(Article.published_at.desc())
        .limit(article_limit)
    ).all()

    # 기사 하나에 관심 태그가 여러 개 붙으면 행이 여러 번 나온다. 먼저 나온 것을 사유로 쓴다.
    candidates: dict[int, tuple[Article, int]] = {}
    for article, tag_id in rows:
        candidates.setdefault(article.id, (article, tag_id))

    existing = set(db.scalars(select(FeedItem.article_id).where(FeedItem.user_id == user.id)))

    created = skipped_no_summary = skipped_duplicate = 0
    for article, matched_tag_id in candidates.values():
        if article.id in existing:
            skipped_duplicate += 1
            continue

        summary = db.scalar(select(Summary).where(Summary.article_id == article.id))
        if summary is None:
            # 요약이 아직 없으면 피드 행을 만들지 않는다. 조회 시점 생성은 금지되어 있으므로
            # 여기서 만들지 않은 기사는 다음 배치에서 다시 후보가 된다.
            skipped_no_summary += 1
            continue

        translation = db.scalar(
            select(Translation).where(
                Translation.summary_id == summary.id,
                Translation.target_language == user.preferred_language,
            )
        )

        db.add(
            FeedItem(
                user_id=user.id,
                article_id=article.id,
                summary_id=summary.id,
                translation_id=translation.id if translation else None,
                matched_tag_id=matched_tag_id,
                # 노출 언어는 별도 컬럼으로 두지 않는다(schema.sql에 feed_items.language가 없다).
                # 위에서 사용자 선호 언어로 고른 translation_id가 곧 노출 언어를 정한다.
            )
        )
        existing.add(article.id)
        created += 1

    db.flush()
    return created, skipped_no_summary, skipped_duplicate


def run_curation(db: Session, *, article_limit: int = 200) -> CurationResult:
    """배치 진입 함수. 실행기 없이 호출·테스트 가능해야 한다."""
    users = list(db.scalars(select(User).where(User.status == "ACTIVE")))
    total_created = total_no_summary = total_dup = 0
    for user in users:
        created, no_summary, dup = curate_for_user(db, user=user, article_limit=article_limit)
        total_created += created
        total_no_summary += no_summary
        total_dup += dup
    return CurationResult(
        scanned_users=len(users),
        created_items=total_created,
        skipped_no_summary=total_no_summary,
        skipped_duplicate=total_dup,
    )


def _interest_tag_ids(db: Session, user_id: int) -> set[int]:
    return set(db.scalars(select(UserTag.tag_id).where(UserTag.user_id == user_id)))


def sync_user_feed(db: Session, *, user: User, article_limit: int = 200) -> FeedSyncResult:
    """관심 태그가 바뀐 뒤 그 사용자의 피드를 현재 관심사에 맞춘다.

    `docs/api-contracts/feed.md` "관심 태그를 바꾸면 피드가 그 자리에서 다시 맞춰진다"의 구현.
    삭제 → 사유 갱신 → 생성 순서다.

    `feed_items`는 `summaries`로부터 재생성할 수 있는 파생 테이블이라 삭제가 안전하다.
    다만 `feed_items.is_read`를 실제로 쓰기 시작하면 삭제가 읽음 상태를 잃는 동작이 된다 —
    그때 다시 검토한다(현재는 백엔드·프론트 어느 쪽도 저장하지 않는다).
    """
    tag_ids = _interest_tag_ids(db, user.id)

    # --- 1) 삭제: 현재 관심 태그가 하나도 붙어 있지 않은 기사의 행 ---
    #
    # matched_tag_id가 빠졌다는 이유로 지우지 않는다. 기사가 [경제, 반도체]이고 사유가
    # '경제'인데 '경제'만 해제했다면 '반도체'가 아직 관심사이므로 행은 남아야 한다.
    # 관심 태그가 0개면 매칭되는 기사가 없으므로 이 규칙 하나로 전부 지워진다 —
    # 그 경우 조회는 전체 최신으로 폴백한다(feed_service.list_feed).
    kept_article_ids = (
        set(
            db.scalars(
                select(ArticleTag.article_id).where(ArticleTag.tag_id.in_(tag_ids))
            )
        )
        if tag_ids
        else set()
    )
    stale_stmt = select(FeedItem.id).where(FeedItem.user_id == user.id)
    if kept_article_ids:
        stale_stmt = stale_stmt.where(FeedItem.article_id.notin_(kept_article_ids))
    # kept가 비어 있으면(관심 태그 0개) 조건을 더하지 않는다 = 그 사용자의 모든 행이 대상.
    stale_ids = list(db.scalars(stale_stmt))
    if stale_ids:
        db.execute(delete(FeedItem).where(FeedItem.id.in_(stale_ids)))
        db.flush()

    # --- 2) 사유 갱신: 살아남은 행의 matched_tag_id가 더 이상 관심사가 아니면 다시 지정 ---
    #
    # 안 그러면 행의 태그 칩 정렬(_order_matched_first)이 사용자가 따르지도 않는 태그를
    # 맨 앞에 세운다.
    repointed = 0
    if tag_ids:
        survivors = list(
            db.scalars(
                select(FeedItem).where(
                    FeedItem.user_id == user.id,
                    # NULL NOT IN (...) 은 NULL이라 걸리지 않는다. 사유가 비어 있는 행도
                    # 대상에 넣어 현재 관심사로 채운다.
                    or_(
                        FeedItem.matched_tag_id.is_(None),
                        FeedItem.matched_tag_id.notin_(tag_ids),
                    ),
                )
            )
        )
        for item in survivors:
            new_tag_id = db.scalar(
                select(ArticleTag.tag_id).where(
                    ArticleTag.article_id == item.article_id,
                    ArticleTag.tag_id.in_(tag_ids),
                )
            )
            if new_tag_id is not None and new_tag_id != item.matched_tag_id:
                item.matched_tag_id = new_tag_id
                repointed += 1
        if repointed:
            db.flush()

    # --- 3) 생성: 새로 걸리는 기사로 행을 만든다 ---
    created, _, _ = curate_for_user(db, user=user, article_limit=article_limit)

    return FeedSyncResult(created=created, deleted=len(stale_ids), repointed=repointed)
