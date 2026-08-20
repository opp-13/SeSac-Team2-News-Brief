"""피드 라우터. 로직은 services에만 둔다. 경로는 api_paths 상수만 사용한다."""

from fastapi import APIRouter, Depends, Query

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user, get_current_user_optional
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
    cursor: str | None = Query(default=None),
    limit: int = Query(default=api_paths.DEFAULT_PAGE_SIZE, ge=1, le=api_paths.MAX_PAGE_SIZE),
    tag: str | None = Query(default=None, description="태그/카테고리 이름. 생략 = 전체"),
    q: str | None = Query(default=None, description="제목·언론사 검색어"),
    user: User | None = Depends(get_current_user_optional),
    db=Depends(get_db),
) -> FeedListResponse:
    """로그인 여부로 두 가지로 동작한다 (docs/api-contracts/feed.md).

    게스트에게 401을 주지 않는다 — 서비스 첫 화면이 비로그인 목록이기 때문이다.
    필터는 태그 **이름**으로 받는다(프런트 필터 칩이 이름을 쓴다).
    """
    rows, next_cursor, has_next = feed_service.list_feed(
        db, user_id=user.id if user else None, limit=limit, cursor=cursor, tag=tag, q=q
    )
    return FeedListResponse(
        items=[
            FeedItemResponse(
                feed_item_id=r.feed_item.id if r.feed_item else None,
                article_id=r.article.id,
                title=r.article.title,
                press=r.press,
                published_at=r.article.published_at,
                language=r.language,
                summary=r.summary_text,
                summary_type=r.summary_type,
                original_url=r.article.url,
                tags=r.tag_names,
                category=r.category,
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
        press=row.press,
        published_at=row.article.published_at,
        language=row.language,
        original_url=row.article.url,
        one_line_summary=contents["ONE_LINE"],
        three_line_summary=contents["THREE_LINE"],
        detail_summary=contents["DETAIL"],
    )

