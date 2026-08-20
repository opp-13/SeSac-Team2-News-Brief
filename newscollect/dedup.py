"""
/sentence_similarity/cosine_similarity.py 호출 용 shim
DB 연결이 안되는 상황에서 임시로 Mockup 해줍니다.
"""

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pymysql

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sentence_similarity import cosine_similarity  # noqa: E402


class _MockCursor:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return []


class _MockConnection:
    def cursor(self):
        return _MockCursor()

    def close(self):
        pass


def _real_db_config() -> dict | None:
    host = os.environ.get("DEDUP_DB_HOST")
    if not host:
        return None
    return {
        "host": host,
        "user": os.environ.get("DEDUP_DB_USER", "root"),
        "password": os.environ.get("DEDUP_DB_PASSWORD", ""),
        "database": os.environ.get("DEDUP_DB_NAME", "db"),
    }


@contextmanager
def _patched_connect():
    real_config = _real_db_config()

    def _connect(**_ignored_hardcoded_kwargs):
        if real_config is not None:
            return pymysql.connect(**real_config)
        return _MockConnection()

    with patch.object(cosine_similarity, "pymysql") as fake_pymysql:
        fake_pymysql.connect.side_effect = _connect
        yield


def dedup_stage(items: list, tag: str) -> list:
    """Drop items whose title is a near-duplicate of one already stored for `tag`.

    No DEDUP_DB_HOST set -> mock DB with zero existing rows, so everything
    passes through unchanged (nothing to compare against yet).
    """
    with _patched_connect():
        return cosine_similarity.dedup_stage(items, tag)
