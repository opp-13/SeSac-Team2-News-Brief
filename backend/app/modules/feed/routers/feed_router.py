"""피드 라우터. 로직은 services에만 둔다. 경로는 api_paths 상수만 사용한다."""

from fastapi import APIRouter, Depends, Query, status

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.feed import api_paths
from app.modules.feed.schemas.feed import (
    FeedDetailResponse,
    FeedItemResponse,
    FeedListResponse,
)
from app.modules.feed.services import feed_service

router = APIRouter(prefix=api_paths.FEED_PREFIX, tags=["feed"])


@router.get(api_paths.FEED_LIST, response_model=FeedListResponse)
def list_feed(
    cursor: int | None = Query(default=None),
    limit: int = Query(default=api_paths.DEFAULT_PAGE_SIZE, ge=1, le=api_paths.MAX_PAGE_SIZE),
    tag_id: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
) -> FeedListResponse:
    rows, next_cursor, has_next = feed_service.list_feed(
        db, user_id=user.id, limit=limit, cursor=cursor, tag_id=tag_id
    )
    return FeedListResponse(
        items=[
            FeedItemResponse(
                feed_item_id=r.feed_item.id,
                article_id=r.article.id,
                title=r.article.title,
                press=r.article.press,
                published_at=r.article.published_at,
                language=r.feed_item.language,
                summary=r.summary_text,
                summary_type=r.summary_type,
                original_url=r.article.url,
                is_bookmarked=r.is_bookmarked,
            )
            for r in rows
        ],
        next_cursor=next_cursor,
        has_next=has_next,
    )


@router.get(api_paths.FEED_DETAIL, response_model=FeedDetailResponse)
def get_feed_detail(
    feed_item_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
) -> FeedDetailResponse:
    row, contents = feed_service.get_feed_detail(db, user_id=user.id, feed_item_id=feed_item_id)
    return FeedDetailResponse(
        feed_item_id=row.feed_item.id,
        article_id=row.article.id,
        title=row.article.title,
        press=row.article.press,
        published_at=row.article.published_at,
        language=row.feed_item.language,
        original_url=row.article.url,
        one_line_summary=contents["ONE_LINE"],
        three_line_summary=contents["THREE_LINE"],
        detail_summary=contents["DETAIL"],
        is_bookmarked=row.is_bookmarked,
    )


@router.post(api_paths.FEED_BOOKMARK, status_code=status.HTTP_204_NO_CONTENT)
def add_bookmark(feed_item_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    feed_service.add_bookmark(db, user_id=user.id, feed_item_id=feed_item_id)
    db.commit()


@router.delete(api_paths.FEED_BOOKMARK, status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(feed_item_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    feed_service.remove_bookmark(db, user_id=user.id, feed_item_id=feed_item_id)
    db.commit()
