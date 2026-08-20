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


def test_translated_articles_are_feed_eligible(db, seed):
    """번역까지 끝난 기사도 피드에 올라간다.

    회귀 방지: `articles.status`는 COLLECTED → SUMMARIZED → TRANSLATED 진행 단계다.
    이전에는 `== 'SUMMARIZED'`로만 걸러서, 수집 파이프라인이 번역까지 마치는 순간
    (A의 processing/db.py가 status를 TRANSLATED로 올린다) 기사가 개인화 피드와
    게스트 목록에서 통째로 사라졌다.
    """
    from app.modules.feed.services import feed_service

    seed["article"].status = "TRANSLATED"
    db.flush()

    result = run_curation(db)
    assert result.created_items == 1

    rows, _, _ = feed_service.list_feed(db, user_id=seed["user"].id, limit=10)
    assert [r.article.id for r in rows] == [seed["article"].id]

    # 게스트 목록에서도 마찬가지다.
    guest_rows, _, _ = feed_service.list_feed(db, user_id=None, limit=10)
    assert seed["article"].id in [r.article.id for r in guest_rows]
