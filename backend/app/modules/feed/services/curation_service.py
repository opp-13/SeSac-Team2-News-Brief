"""콘텐츠 큐레이션 로직 (feed_items 생성).

실행기 비의존: 스케줄러/큐 데코레이터를 붙이지 않는다. 인자를 받아 결과를 반환하는 함수만 둔다.
`feed_items` INSERT는 C 전용이다. summaries/translations는 읽기만 한다.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models.user import User  # 같은 담당(C) 소유 모듈이므로 참조 허용
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import Article, Summary, Translation
from app.modules.feed.models.tag import Tag, UserTag

# [OPEN] 태그 매칭 기준. 현재는 기사 제목 부분일치로 임시 구현.
# 기사-태그 매핑 테이블(article_tags)이 스키마에 있으면 그쪽을 쓰는 것이 맞다 → schema.sql 확인 필요.
ARTICLE_STATUS_READY = "SUMMARIZED"  # [SCHEMA-CHECK] 실제 상태값 확인 필요


@dataclass
class CurationResult:
    scanned_users: int
    created_items: int
    skipped_no_summary: int
    skipped_duplicate: int


def curate_for_user(db: Session, *, user: User, article_limit: int = 200) -> tuple[int, int, int]:
    """한 사용자의 관심 태그에 맞는 기사로 feed_items를 만든다. (생성, 요약없음, 중복) 반환."""
    tag_ids = list(db.scalars(select(UserTag.tag_id).where(UserTag.user_id == user.id)))
    if not tag_ids:
        return 0, 0, 0

    tag_names = list(db.scalars(select(Tag.name).where(Tag.id.in_(tag_ids))))

    articles = list(
        db.scalars(
            select(Article)
            .where(Article.status == ARTICLE_STATUS_READY)
            .order_by(Article.published_at.desc())
            .limit(article_limit)
        )
    )

    existing = set(
        db.scalars(select(FeedItem.article_id).where(FeedItem.user_id == user.id))
    )

    created = skipped_no_summary = skipped_duplicate = 0
    for article in articles:
        if not _matches(article, tag_names):
            continue
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
                matched_tag_id=tag_ids[0] if tag_ids else None,  # [OPEN] 매칭 태그 기록 방식 확정 필요
                language=user.preferred_language,
            )
        )
        existing.add(article.id)
        created += 1

    db.flush()
    return created, skipped_no_summary, skipped_duplicate


def _matches(article: Article, tag_names: list[str]) -> bool:
    title = (article.title or "").lower()
    return any(name.lower() in title for name in tag_names)


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
