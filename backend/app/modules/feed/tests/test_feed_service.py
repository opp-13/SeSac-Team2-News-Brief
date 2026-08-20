"""피드 조회: 정상 경로 1개 + 실패 경로 1개."""

from datetime import datetime, timezone

import pytest

from app.common.exceptions import NotFoundError
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import Article
from app.modules.feed.services import feed_service


def _make_feed_item(db, seed):
    item = FeedItem(
        user_id=seed["user"].id,
        article_id=seed["article"].id,
        summary_id=seed["summary"].id,
        # 실제로 존재하는 번역을 가리킨다. V2에서 translation_id에 FK가 걸리므로
        # 없는 id를 박아 두면 MySQL에서 INSERT 자체가 실패한다.
        translation_id=seed["translation"].id,
        matched_tag_id=seed["tag"].id,
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
    # 요약 원문("원문 언어 요약 3줄")이 아니라 저장된 번역이 노출된다.
    assert rows[0].summary_text == "번역된 요약 3줄"
    assert rows[0].article.url == "https://news.example.com/1"
    assert has_next is False and next_cursor is None


def test_detail_of_other_users_item_raises_not_found(db, seed):
    """실패: 남의 피드 행은 404. 존재 여부를 노출하지 않는다."""
    item = _make_feed_item(db, seed)

    with pytest.raises(NotFoundError):
        feed_service.get_feed_detail(db, user_id=seed["other"].id, feed_item_id=item.id)


def test_personal_feed_tag_filter_uses_article_tags(db, seed):
    """태그 칩은 로그인 여부와 상관없이 "그 태그가 붙은 기사"를 뜻해야 한다.

    회귀 방지: 이전에는 개인화 경로가 `feed_items.matched_tag_id`로 걸렀다. 그 컬럼에는
    큐레이션이 고른 사유 **하나만** 들어가므로, 기사에 붙은 다른 태그로 필터하면 0건이 됐다.
    프런트는 로그인 시 필터 칩을 사용자의 관심 태그로 그리기 때문에, 관심 태그를 바꾸면
    모든 칩이 빈 목록이 되는 증상으로 나타났다.
    """
    from app.modules.feed.models.read_only import ArticleTag
    from app.modules.feed.models.tag import TAG_TYPE_CATEGORY, Tag

    # 기사에 'IT' 태그를 붙이되, 피드 행의 노출 사유(matched_tag_id)는 'AI'로 남겨 둔다.
    it_tag = Tag(name="IT", slug="it", tag_type=TAG_TYPE_CATEGORY)
    db.add(it_tag)
    db.flush()
    # 'AI' 매핑은 conftest가 이미 넣었다. 여기서는 'IT'만 더한다.
    db.add(ArticleTag(article_id=seed["article"].id, tag_id=it_tag.id))
    item = _make_feed_item(db, seed)
    assert item.matched_tag_id == seed["tag"].id  # 사유는 'AI'
    db.flush()

    rows, _, _ = feed_service.list_feed(
        db, user_id=seed["user"].id, limit=10, tag="IT"
    )

    # 사유가 'AI'여도 기사에 'IT'가 붙어 있으므로 'IT' 칩에서 보여야 한다.
    assert [r.article.id for r in rows] == [seed["article"].id]


def test_personal_feed_tag_filter_excludes_untagged_article(db, seed):
    """실패 경로: 그 태그가 붙지 않은 기사는 빠진다."""
    _make_feed_item(db, seed)

    rows, _, _ = feed_service.list_feed(
        db, user_id=seed["user"].id, limit=10, tag="AI"
    )

    # conftest가 'AI'를 붙여 뒀으므로 'AI' 칩에는 잡힌다.
    assert [r.article.id for r in rows] == [seed["article"].id]

    # 붙지 않은 태그로 거르면 빈 목록이다.
    rows, _, _ = feed_service.list_feed(db, user_id=seed["user"].id, limit=10, tag="없는태그")
    assert rows == []


def test_user_without_interest_tags_gets_the_guest_list(db, seed):
    """관심 태그가 0개인 로그인 사용자는 전체 최신 목록을 본다.

    설정 화면이 "태그를 선택하지 않으면 전체 최신 뉴스를 보여줍니다"로 약속하고 있다.
    feed_items만 읽으면 빈 화면이 된다 (docs/api-contracts/feed.md).
    """
    other = seed["other"]  # conftest에서 관심 태그를 주지 않은 계정

    rows, _, _ = feed_service.list_feed(db, user_id=other.id, limit=10)
    guest_rows, _, _ = feed_service.list_feed(db, user_id=None, limit=10)

    # 규칙은 "게스트와 동일한 목록"이다. 건수를 따로 박지 않고 게스트 결과와 맞춰 비교한다.
    assert [r.article.id for r in rows] == [r.article.id for r in guest_rows]
    assert rows  # 빈 목록이면 폴백이 의미가 없다
    # 피드 행이 아니므로 feed_item은 None이고, 프론트는 feedItemId를 null로 받는다.
    assert all(r.feed_item is None for r in rows)


def _extra_article(db, seed, *, title, hours_newer, url_suffix):
    """seed 기사보다 hours_newer 시간 뒤에 발행된 기사를 추가한다."""
    from datetime import timedelta

    from app.modules.feed.models.read_only import Article, ArticleTag, Summary

    base = seed["article"]
    a = Article(
        title=title,
        url=f"https://news.example.com/{url_suffix}",
        url_hash=str(url_suffix) * 8 + "c" * (64 - len(str(url_suffix)) * 8),
        source_id=base.source_id,
        language="ko",
        status="SUMMARIZED",
        published_at=base.published_at + timedelta(hours=hours_newer),
    )
    db.add(a)
    db.flush()
    db.add(ArticleTag(article_id=a.id, tag_id=seed["tag"].id))
    db.add(
        Summary(
            article_id=a.id,
            summary_type="THREE_LINE",
            content=f"{title} 요약",
            language="ko",
            provider="anthropic",
            model_name="claude-sonnet-5",
            created_at=base.published_at,
        )
    )
    db.flush()
    return a


def test_feed_is_ordered_newest_first(db, seed):
    """발행 최신순으로 나온다 — id 순서가 아니다.

    회귀 방지: 이전에는 `id DESC`로 정렬했는데, id는 수집 순서라 발행 순서와 다르다.
    시드처럼 최신 기사가 먼저 INSERT되면 id DESC가 **가장 오래된 기사를 맨 위**에 올렸다.
    """
    newer = _extra_article(db, seed, title="더 최신 기사", hours_newer=5, url_suffix=91)
    older = _extra_article(db, seed, title="더 오래된 기사", hours_newer=-5, url_suffix=92)

    # id는 나중에 만든 older가 더 크다 — id 정렬이면 older가 위로 온다.
    assert older.id > newer.id

    rows, _, _ = feed_service.list_feed(db, user_id=None, limit=10)
    ids = [r.article.id for r in rows]
    assert ids.index(newer.id) < ids.index(older.id)
    assert rows[0].article.id == newer.id


def test_cursor_pagination_walks_without_gaps_or_repeats(db, seed):
    """커서로 이어 읽어도 빠지거나 겹치는 기사가 없다."""
    _extra_article(db, seed, title="A", hours_newer=5, url_suffix=93)
    _extra_article(db, seed, title="B", hours_newer=-5, url_suffix=94)

    seen: list[int] = []
    cursor = None
    for _ in range(10):
        rows, cursor, has_next = feed_service.list_feed(db, user_id=None, limit=2, cursor=cursor)
        seen.extend(r.article.id for r in rows)
        if not has_next:
            break

    all_ids = [a.id for a in db.query(Article).all()]
    assert sorted(seen) == sorted(all_ids)   # 빠진 것 없음
    assert len(seen) == len(set(seen))       # 겹친 것 없음


def test_malformed_cursor_is_rejected(db, seed):
    """실패 경로: 깨진 커서는 INVALID_CURSOR로 거부한다 (계약 정의)."""
    from app.common.exceptions import BadRequestError

    with pytest.raises(BadRequestError):
        feed_service.list_feed(db, user_id=None, limit=10, cursor="!!not-a-cursor!!")


def test_guest_list_shows_translation_over_original(db, seed):
    """번역이 있으면 원문 요약 대신 번역을 노출한다.

    이 서비스의 핵심이 번역 요약 제공이다(CLAUDE.md §1). 이전에는 게스트 경로가
    "선호 언어를 모른다"는 이유로 translations를 조회조차 하지 않아, 영어 기사는
    영어 요약이 그대로 나갔다.
    """
    rows, _, _ = feed_service.list_feed(db, user_id=None, limit=10)
    row = next(r for r in rows if r.article.id == seed["article"].id)

    # conftest: 요약은 "원문 언어 요약 3줄", ko 번역은 "번역된 요약 3줄"
    assert row.summary_text == "번역된 요약 3줄"
    assert row.language == "ko"


def test_guest_list_falls_back_to_original_when_no_translation(db, seed):
    """번역이 없으면 원문 요약을 쓴다 — 조회 시점에 번역을 만들지 않는다."""
    from app.modules.feed.models.read_only import Translation

    db.query(Translation).delete()
    db.flush()

    rows, _, _ = feed_service.list_feed(db, user_id=None, limit=10)
    row = next(r for r in rows if r.article.id == seed["article"].id)

    assert row.summary_text == "원문 언어 요약 3줄"


def test_guest_list_ignores_failed_translation(db, seed):
    """실패한 번역은 본문이 오류 문구라 노출하지 않는다."""
    from app.modules.feed.models.read_only import Translation

    t = db.query(Translation).first()
    t.status = "FAILED"
    db.flush()

    rows, _, _ = feed_service.list_feed(db, user_id=None, limit=10)
    row = next(r for r in rows if r.article.id == seed["article"].id)

    assert row.summary_text == "원문 언어 요약 3줄"


def test_user_without_tags_gets_their_preferred_language(db, seed):
    """관심 태그가 없는 로그인 사용자는 목록만 게스트와 같고, 언어는 본인 설정을 따른다."""
    from app.modules.feed.models.read_only import Summary, Translation

    other = seed["other"]
    other.preferred_language = "en"
    summary = db.query(Summary).first()
    db.add(
        Translation(
            summary_id=summary.id,
            target_language="en",
            translated_content="English summary",
            provider="google",
            model_name="translate_v2",
            status="DONE",
            created_at=summary.created_at,
        )
    )
    db.flush()

    rows, _, _ = feed_service.list_feed(db, user_id=other.id, limit=10)
    row = next(r for r in rows if r.article.id == seed["article"].id)

    assert row.summary_text == "English summary"
    assert row.language == "en"
