"""feed 모듈 테스트 픽스처.

DB는 기본이 SQLite in-memory고, `TEST_DATABASE_URL`을 주면 로컬 MySQL로 돌아간다
(`app/db/testing.py` 참고 — 모델·스키마 어긋남은 MySQL 모드에서만 잡힌다).
(통합 이후 각 담당이 자기 모듈을 테스트한다 — CLAUDE.md §3)
"""

from datetime import datetime, timezone

import pytest

from app.db.testing import make_engine, new_session, prepare_schema
from app.modules.auth.models.user import User  # noqa: F401
from app.modules.feed.models.feed_item import FeedItem  # noqa: F401
from app.modules.feed.models.read_only import (  # noqa: F401
    Article,
    ArticleTag,
    NewsSource,
    Summary,
    Translation,
)
from app.modules.feed.models.tag import TAG_TYPE_KEYWORD, Tag, UserTag  # noqa: F401


@pytest.fixture()
def db():
    engine = make_engine()
    prepare_schema(engine)
    session = new_session(engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seed(db):
    """큐레이션·피드 조회 테스트에 필요한 최소 시드 데이터."""
    now = datetime.now(timezone.utc)

    user = User(
        email="user@test.com",
        password_hash="x",
        nickname="테스터",
        preferred_language="ko",
        status="ACTIVE",
    )
    other = User(
        email="other@test.com",
        password_hash="x",
        nickname="다른사람",
        preferred_language="ko",
        status="ACTIVE",
    )
    db.add_all([user, other])
    db.flush()

    tag = Tag(name="AI", slug="ai", tag_type=TAG_TYPE_KEYWORD)
    db.add(tag)
    # 언론사 이름은 articles가 직접 갖지 않고 news_sources를 조인해서 얻는다
    # (schema.sql에 articles.press 컬럼이 없다).
    source = NewsSource(name="테스트일보", provider="RSS")
    db.add(source)
    db.flush()

    db.add(UserTag(user_id=user.id, tag_id=tag.id))

    # 요약 있는 기사 — 큐레이션 대상, 피드 목록 조회 기준
    # 스키마 V2가 파티셔닝을 없애 articles PK가 id 단일이 됐다 → id를 직접 박지 않아도 된다.
    article = Article(
        title="AI 반도체 시장 확대",
        url="https://news.example.com/1",
        # NOT NULL + 단독 UNIQUE. 실제로는 A의 수집기가 정규화 URL의 SHA-256으로 채운다.
        url_hash="a" * 64,
        # NOT NULL + 단독 UNIQUE. 실제로는 A의 수집기가 정규화 URL의 SHA-256으로 채운다.
        source_id=source.id,
        language="ko",
        status="SUMMARIZED",
        published_at=now,
    )
    # 요약 없는 기사 — skipped_no_summary 검증용
    article_no_summary = Article(
        title="AI 의료 혁신",
        url="https://news.example.com/2",
        url_hash="b" * 64,
        source_id=None,
        language="ko",
        status="SUMMARIZED",
        published_at=now,
    )
    db.add_all([article, article_no_summary])
    db.flush()

    # 큐레이션은 제목이 아니라 `article_tags` 매핑으로 매칭한다. 두 기사 모두 후보가 되게
    # 태그를 붙여 두고, 요약 유무로만 갈리게 한다 — 그래야 skipped_no_summary가 검증된다.
    db.add_all(
        [
            ArticleTag(article_id=article.id, tag_id=tag.id),
            ArticleTag(article_id=article_no_summary.id, tag_id=tag.id),
        ]
    )
    db.flush()

    summary = Summary(
        article_id=article.id,
        summary_type="THREE_LINE",
        content="원문 언어 요약 3줄",
        language="ko",
        provider="anthropic",
        model_name="claude-sonnet-5",
        created_at=now,
    )
    db.add(summary)
    db.flush()

    # 저장된 번역. 피드는 번역이 있으면 번역을 우선 노출하므로, 요약 본문과 다른 문자열을
    # 넣어야 "어느 쪽이 쓰였는지"를 테스트가 실제로 구분할 수 있다.
    translation = Translation(
        summary_id=summary.id,
        target_language="ko",
        translated_title="AI 반도체 시장 확대",
        translated_content="번역된 요약 3줄",
        provider="anthropic",
        model_name="claude-sonnet-5",
        status="DONE",
        created_at=now,
    )
    db.add(translation)
    db.flush()

    db.commit()

    return {
        "user": user,
        "other": other,
        "tag": tag,
        "article": article,
        "article_no_summary": article_no_summary,
        "summary": summary,
        "translation": translation,
        "source": source,
    }
