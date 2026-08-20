"""큐레이션 배치: 정상 경로 1개 + 실패(스킵) 경로 1개. 실행기 없이 함수 단위로 검증한다."""

from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.services.curation_service import run_curation


def test_curation_creates_feed_item_for_matching_tag(db, seed):
    """정상: 관심 태그와 매칭되고 요약이 있는 기사만 feed_items로 생성된다."""
    result = run_curation(db)

    items = db.query(FeedItem).all()
    assert result.created_items == 1
    assert len(items) == 1
    assert items[0].article_id == seed["article"].id
    # 요약이 없는 기사는 생성되지 않고 스킵 카운트로 남는다.
    assert result.skipped_no_summary == 1


def test_curation_is_idempotent(db, seed):
    """실패 방지: 같은 배치를 두 번 돌려도 중복 피드 행을 만들지 않는다."""
    run_curation(db)
    second = run_curation(db)

    assert second.created_items == 0
    assert second.skipped_duplicate == 1
    assert db.query(FeedItem).count() == 1
