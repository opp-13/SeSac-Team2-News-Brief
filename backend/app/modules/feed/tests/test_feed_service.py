"""피드 조회: 정상 경로 1개 + 실패 경로 1개."""

from datetime import datetime, timezone

import pytest

from app.common.exceptions import NotFoundError
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.services import feed_service


def _make_feed_item(db, seed):
    item = FeedItem(
        user_id=seed["user"].id,
        article_id=seed["article"].id,
        summary_id=seed["summary"].id,
        translation_id=100,
        matched_tag_id=seed["tag"].id,
        language="ko",
        created_at=datetime.now(timezone.utc),
    )
    db.add(item)
    db.flush()
    return item


def test_list_feed_returns_stored_translation(db, seed):
    """정상: 저장된 번역본을 그대로 반환한다 (조회 시점 생성 없음)."""
    _make_feed_item(db, seed)

    rows, next_cursor, has_next = feed_service.list_feed(db, user_id=seed["user"].id, limit=10)

    assert len(rows) == 1
    assert rows[0].summary_text == "번역된 요약 3줄"
    assert rows[0].article.url == "https://news.example.com/1"
    assert has_next is False and next_cursor is None


def test_detail_of_other_users_item_raises_not_found(db, seed):
    """실패: 남의 피드 행은 404. 존재 여부를 노출하지 않는다."""
    item = _make_feed_item(db, seed)

    with pytest.raises(NotFoundError):
        feed_service.get_feed_detail(db, user_id=seed["other"].id, feed_item_id=item.id)
