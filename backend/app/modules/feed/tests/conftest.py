"""feed 모듈 테스트 픽스처.

DB는 SQLite in-memory, 외부 의존 없이 돌린다.
(통합 이후 각 담당이 자기 모듈을 테스트한다 — CLAUDE.md §3)
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.modules.auth.models.user import User  # noqa: F401
from app.modules.feed.models.bookmark import Bookmark  # noqa: F401
from app.modules.feed.models.feed_item import FeedItem  # noqa: F401
from app.modules.feed.models.read_only import Article, Summary, Translation  # noqa: F401
from app.modules.feed.models.tag import Tag, UserTag  # noqa: F401


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


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

    tag = Tag(name="AI", category="기술")
    db.add(tag)
    db.flush()

    db.add(UserTag(user_id=user.id, tag_id=tag.id))

    # 요약 있는 기사 — 큐레이션 대상, 피드 목록 조회 기준
    article = Article(
        title="AI 반도체 시장 확대",
        url="https://news.example.com/1",
        press="테스트일보",
        status="SUMMARIZED",
        published_at=now,
    )
    # 요약 없는 기사 — skipped_no_summary 검증용
    article_no_summary = Article(
        title="AI 의료 혁신",
        url="https://news.example.com/2",
        press=None,
        status="SUMMARIZED",
        published_at=now,
    )
    db.add_all([article, article_no_summary])
    db.flush()

    summary = Summary(
        article_id=article.id,
        summary_type="THREE_LINE",
        content="번역된 요약 3줄",
        created_at=now,
    )
    db.add(summary)
    db.flush()

    db.commit()

    return {
        "user": user,
        "other": other,
        "tag": tag,
        "article": article,
        "summary": summary,
    }
