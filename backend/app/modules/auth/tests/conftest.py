"""auth 모듈 테스트 픽스처.

DB는 기본이 SQLite in-memory고 `TEST_DATABASE_URL`을 주면 로컬 MySQL로 돌아간다
(`app/db/testing.py`). Redis는 최소 페이크로 대체해 외부 의존 없이 돌린다.
(통합 이후 각 담당이 자기 모듈을 테스트한다 — CLAUDE.md §3)
"""

import time

import pytest

from app.db.testing import make_engine, new_session, prepare_schema
from app.modules.auth.models.user import User  # noqa: F401  (테이블 등록용)


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
