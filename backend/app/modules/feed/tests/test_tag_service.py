"""관심 태그 저장: 정상 경로 + 실패 경로.

핵심 회귀 방지: **태그를 저장하면 그 자리에서 피드가 채워져야 한다.**
`feed_items`는 배치만 채우는 테이블인데 배치 트리거가 없어서, 가입해서 관심 태그를 골라도
피드가 영원히 비어 있던 문제가 있었다.
"""

import pytest

from app.common.exceptions import NotFoundError
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.services import tag_service


def _feed_count(db, user_id: int) -> int:
    return db.query(FeedItem).filter_by(user_id=user_id).count()


def test_saving_tags_fills_feed_immediately(db, seed):
    """정상: 관심 태그를 저장하면 그 태그가 붙은 기사로 피드 행이 만들어진다."""
    other = seed["other"]  # 관심 태그도 피드도 없는 계정
    assert _feed_count(db, other.id) == 0

    tags, created = tag_service.replace_user_tags(db, other, [seed["tag"].id])

    assert [t.name for t in tags] == ["AI"]
    assert created == 1
    items = db.query(FeedItem).filter_by(user_id=other.id).all()
    assert len(items) == 1
    # 요약이 있는 기사만 들어간다. 요약 없는 기사는 같은 태그가 붙어 있어도 제외된다.
    assert items[0].article_id == seed["article"].id
    # 노출 사유는 실제로 매칭된 태그다.
    assert items[0].matched_tag_id == seed["tag"].id


def test_saving_same_tags_twice_does_not_duplicate(db, seed):
    """설정 화면에서 저장을 두 번 눌러도 피드 행이 늘지 않는다."""
    other = seed["other"]
    tag_service.replace_user_tags(db, other, [seed["tag"].id])

    _, created_again = tag_service.replace_user_tags(db, other, [seed["tag"].id])

    assert created_again == 0
    assert _feed_count(db, other.id) == 1


def test_removing_all_tags_clears_the_feed(db, seed):
    """관심 태그를 모두 해제하면 피드 행도 사라진다.

    조회는 게스트와 같은 전체 최신 목록으로 폴백하므로 화면이 비지는 않는다
    (test_feed_service의 폴백 테스트 참고).
    """
    other = seed["other"]
    tag_service.replace_user_tags(db, other, [seed["tag"].id])
    assert _feed_count(db, other.id) == 1

    tags, created = tag_service.replace_user_tags(db, other, [])

    assert tags == []
    assert created == 0
    assert _feed_count(db, other.id) == 0


def test_removing_one_tag_keeps_rows_matched_by_another(db, seed):
    """관심 태그 하나를 빼도, 그 기사에 다른 관심 태그가 붙어 있으면 행은 남는다.

    `matched_tag_id`가 빠졌다는 이유로 지우면 안 된다는 규칙의 회귀 방지다.
    """
    from app.modules.feed.models.read_only import ArticleTag
    from app.modules.feed.models.tag import TAG_TYPE_CATEGORY, Tag

    other = seed["other"]
    it_tag = Tag(name="IT", slug="it", tag_type=TAG_TYPE_CATEGORY)
    db.add(it_tag)
    db.flush()
    # 기사에 'AI'(conftest)와 'IT'를 모두 붙인다.
    db.add(ArticleTag(article_id=seed["article"].id, tag_id=it_tag.id))
    db.flush()

    # 두 태그를 다 관심사로 두면 행이 생긴다. 사유는 먼저 매칭된 쪽이다.
    tag_service.replace_user_tags(db, other, [seed["tag"].id, it_tag.id])
    assert _feed_count(db, other.id) == 1

    # 'AI'만 뺀다 → 'IT'가 남아 있으므로 행은 유지되고, 사유는 'IT'로 다시 지정된다.
    tag_service.replace_user_tags(db, other, [it_tag.id])

    items = db.query(FeedItem).filter_by(user_id=other.id).all()
    assert len(items) == 1
    assert items[0].matched_tag_id == it_tag.id


def test_removing_the_only_matching_tag_drops_the_row(db, seed):
    """실패 경로: 관심사가 하나도 안 붙은 기사의 행은 지워진다."""
    from app.modules.feed.models.tag import TAG_TYPE_CATEGORY, Tag

    other = seed["other"]
    tag_service.replace_user_tags(db, other, [seed["tag"].id])
    assert _feed_count(db, other.id) == 1

    # 기사에 붙어 있지 않은 다른 태그로 갈아탄다.
    unrelated = Tag(name="스포츠", slug="sports", tag_type=TAG_TYPE_CATEGORY)
    db.add(unrelated)
    db.flush()
    tag_service.replace_user_tags(db, other, [unrelated.id])

    assert _feed_count(db, other.id) == 0


def test_unknown_tag_id_is_rejected_without_touching_existing(db, seed):
    """실패: 없는 태그 id가 섞이면 거부하고, 기존 관심 태그를 지우지 않는다."""
    user = seed["user"]  # conftest에서 'AI'를 이미 갖고 있다

    with pytest.raises(NotFoundError):
        tag_service.replace_user_tags(db, user, [seed["tag"].id, 999_999])

    assert [t.name for t in tag_service.list_user_tags(db, user.id)] == ["AI"]


def test_list_all_tags_hides_inactive(db, seed):
    """선택 가능한 태그 목록은 활성 태그만 내려준다.

    `tags`에는 수집기가 쓰는 카테고리 전체가 들어 있지만(현재 63개) 필터 칩에 다 늘어놓지
    않는다. `is_active`는 화면 노출 여부만 뜻하고, 수집기는 비활성 태그로도 태깅한다.
    """
    from app.modules.feed.models.tag import TAG_TYPE_CATEGORY, Tag

    db.add(Tag(name="크리켓", slug="cricket", tag_type=TAG_TYPE_CATEGORY, is_active=False))
    db.flush()

    names = [t.name for t in tag_service.list_all_tags(db)]

    assert "크리켓" not in names
    assert "AI" in names  # conftest의 활성 태그는 그대로 보인다
