"""피드 조회 서비스.

**금지: 이 파일에서 Bedrock/AI 서비스를 호출하지 않는다** (CLAUDE.md §9, SKILL §4-1).
저장된 summaries/translations만 읽고, 없으면 null 또는 제외로 처리한다.
캐시를 붙이더라도 캐시 미스는 MySQL 조회까지만 이어진다.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import NotFoundError
from app.modules.feed.models.bookmark import Bookmark
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import Article, Summary, Translation

# [PROV-F15] 목록에 노출할 기본 요약 타입. "요약 3종 저장 여부"가 미결이므로 상수로 분리해 둔다.
LIST_SUMMARY_TYPE = "THREE_LINE"


@dataclass
class FeedRow:
    feed_item: FeedItem
    article: Article
    summary_text: str | None
    summary_type: str | None
    is_bookmarked: bool


def _resolve_summary_text(
    db: Session, summary_id: int | None, translation_id: int | None, language: str
) -> tuple[str | None, str | None]:
    """저장된 번역 > 저장된 요약 순으로 사용. 없으면 (None, None) — 생성하지 않는다."""
    if translation_id is not None:
        translation = db.get(Translation, translation_id)
        if translation is not None and translation.target_language == language:
            summary = db.get(Summary, translation.summary_id) if summary_id is None else db.get(Summary, summary_id)
            return translation.content, (summary.summary_type if summary else None)
    if summary_id is not None:
        summary = db.get(Summary, summary_id)
        if summary is not None:
            return summary.content, summary.summary_type
    return None, None


def list_feed(
    db: Session,
    *,
    user_id: int,
    limit: int,
    cursor: int | None = None,
    tag_id: int | None = None,
) -> tuple[list[FeedRow], int | None, bool]:
    stmt = (
        select(FeedItem, Article)
        .join(Article, Article.id == FeedItem.article_id)
        .where(FeedItem.user_id == user_id)
        .order_by(FeedItem.id.desc())
        .limit(limit + 1)  # has_next 판별용 1건 초과 조회
    )
    if cursor is not None:
        stmt = stmt.where(FeedItem.id < cursor)
    if tag_id is not None:
        stmt = stmt.where(FeedItem.matched_tag_id == tag_id)

    rows = list(db.execute(stmt).all())
    has_next = len(rows) > limit
    rows = rows[:limit]

    bookmarked = set(
        db.scalars(
            select(Bookmark.feed_item_id).where(
                Bookmark.user_id == user_id,
                Bookmark.feed_item_id.in_([r[0].id for r in rows] or [0]),
            )
        )
    )

    result: list[FeedRow] = []
    for feed_item, article in rows:
        text, stype = _resolve_summary_text(
            db, feed_item.summary_id, feed_item.translation_id, feed_item.language
        )
        result.append(
            FeedRow(
                feed_item=feed_item,
                article=article,
                summary_text=text,
                summary_type=stype,
                is_bookmarked=feed_item.id in bookmarked,
            )
        )

    next_cursor = result[-1].feed_item.id if result and has_next else None
    return result, next_cursor, has_next


def get_feed_detail(db: Session, *, user_id: int, feed_item_id: int) -> tuple[FeedRow, dict[str, str | None]]:
    feed_item = db.get(FeedItem, feed_item_id)
    if feed_item is None or feed_item.user_id != user_id:
        # 남의 피드 행 존재 여부를 노출하지 않기 위해 동일하게 404 처리한다.
        raise NotFoundError("FEED_ITEM_NOT_FOUND")

    article = db.get(Article, feed_item.article_id)
    if article is None:
        raise NotFoundError("ARTICLE_NOT_FOUND")

    # 저장된 요약 3종만 조회. 없으면 None (생성하지 않는다).
    summaries = {
        s.summary_type: s
        for s in db.scalars(select(Summary).where(Summary.article_id == article.id))
    }
    translations = {
        t.summary_id: t
        for t in db.scalars(
            select(Translation).where(
                Translation.summary_id.in_([s.id for s in summaries.values()] or [0]),
                Translation.target_language == feed_item.language,
            )
        )
    }

    def pick(summary_type: str) -> str | None:
        s = summaries.get(summary_type)
        if s is None:
            return None
        t = translations.get(s.id)
        return t.content if t is not None else s.content

    is_bookmarked = (
        db.scalar(
            select(Bookmark.id).where(
                Bookmark.user_id == user_id, Bookmark.feed_item_id == feed_item_id
            )
        )
        is not None
    )

    row = FeedRow(
        feed_item=feed_item,
        article=article,
        summary_text=pick(LIST_SUMMARY_TYPE),
        summary_type=LIST_SUMMARY_TYPE,
        is_bookmarked=is_bookmarked,
    )
    contents = {
        "ONE_LINE": pick("ONE_LINE"),
        "THREE_LINE": pick("THREE_LINE"),
        "DETAIL": pick("DETAIL"),
    }
    return row, contents


def add_bookmark(db: Session, *, user_id: int, feed_item_id: int) -> None:
    feed_item = db.get(FeedItem, feed_item_id)
    if feed_item is None or feed_item.user_id != user_id:
        raise NotFoundError("FEED_ITEM_NOT_FOUND")
    exists = db.scalar(
        select(Bookmark.id).where(
            Bookmark.user_id == user_id, Bookmark.feed_item_id == feed_item_id
        )
    )
    if exists is None:
        db.add(Bookmark(user_id=user_id, feed_item_id=feed_item_id))
        db.flush()


def remove_bookmark(db: Session, *, user_id: int, feed_item_id: int) -> None:
    bookmark = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == user_id, Bookmark.feed_item_id == feed_item_id
        )
    )
    if bookmark is None:
        raise NotFoundError("BOOKMARK_NOT_FOUND")
    db.delete(bookmark)
    db.flush()
