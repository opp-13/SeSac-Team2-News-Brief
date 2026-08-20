"""auth 모듈 테스트 픽스처.

DB는 SQLite in-memory, Redis는 최소 페이크로 대체해 외부 의존 없이 돌린다.
(통합 이후 각 담당이 자기 모듈을 테스트한다 — CLAUDE.md §3)
"""

import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.modules.auth.models.user import User  # noqa: F401  (테이블 등록용)


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


class FakeRedis:
    def __init__(self):
        self._store: dict[str, tuple[str, float | None]] = {}

    def setex(self, key, ttl, value):
        self._store[key] = (value, time.time() + ttl)

    def get(self, key):
        item = self._store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and expires_at < time.time():
            del self._store[key]
            return None
        return value

    def delete(self, key):
        self._store.pop(key, None)


@pytest.fixture()
def redis():
    return FakeRedis()
