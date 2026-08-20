"""테스트용 DB 엔진.

기본은 SQLite in-memory다 — 외부 의존 없이 빠르게 돌아간다.
`TEST_DATABASE_URL`을 주면 그 DB에 붙는다. 로컬 MySQL로 돌릴 때 쓴다.

    # 1) 테스트 스키마를 Alembic으로 올린다 (최초 1회, 스키마가 바뀌면 다시)
    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS news_ai_test \
      DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_0900_ai_ci"
    DATABASE_URL="mysql+pymysql://root:PW@127.0.0.1:3306/news_ai_test?charset=utf8mb4" \
      .venv/bin/alembic upgrade head

    # 2) 그 스키마에 붙여서 테스트
    TEST_DATABASE_URL="mysql+pymysql://root:PW@127.0.0.1:3306/news_ai_test?charset=utf8mb4" \
      .venv/bin/python -m pytest app

**MySQL 모드에서는 테이블을 만들지 않는다.** 스키마는 Alembic이 올린 것을 그대로 쓰고,
테스트 사이에는 데이터만 비운다.

이게 이 파일의 핵심이다. 모델로 테이블을 만들면(`create_all`) **모델과 스키마가 어긋나도
테스트가 통과한다** — 어긋난 모델대로 테이블이 생기기 때문이다. 실제로 `read_only.py`가
`NOT NULL` 컬럼 5개(`articles.url_hash` 포함)를 빠뜨린 채 SQLite 테스트를 전부 통과한 적이
있고, 진짜 스키마에 붙이자마자 INSERT가 깨졌다. Alembic이 만든 스키마에 붙어야 그게 잡힌다.

SQLite 모드는 그 검증을 못 하지만 빠르다. 평소에는 SQLite로 돌리고,
스키마·모델을 건드린 뒤에는 MySQL로 한 번 돌린다.
"""

import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base

SQLITE_URL = "sqlite+pysqlite:///:memory:"


def test_database_url() -> str | None:
    """MySQL 등 실제 DB로 돌릴 때의 접속 URL. 없으면 SQLite 모드."""
    return os.getenv("TEST_DATABASE_URL") or None


def make_engine() -> Engine:
    url = test_database_url()
    if url is not None:
        return create_engine(url, pool_pre_ping=True)

    engine = create_engine(SQLITE_URL)

    # SQLite는 FK를 기본으로 **무시한다.** 그대로 두면 보관 배치의 hard delete가 실제로는
    # ON DELETE CASCADE 없이 도는 것을 검증하게 되고, MySQL에서만 다르게 동작한다.
    # retention_service는 "summaries를 지우면 translations/feed_items가 따라 지워진다"에
    # 의존하므로, 이 PRAGMA가 없으면 테스트가 통과해도 아무것도 보증하지 못한다.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):  # noqa: ANN001, ANN202, ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def prepare_schema(engine: Engine) -> None:
    """SQLite면 모델로 테이블을 만들고, 실제 DB면 Alembic 스키마를 두고 데이터만 비운다."""
    if test_database_url() is None:
        Base.metadata.create_all(engine)
        return

    # 모델이 있는 테이블만 비운다. A·B 소유 테이블은 모델이 없고 테스트도 쓰지 않는다.
    is_mysql = engine.dialect.name == "mysql"
    with engine.begin() as conn:
        if is_mysql:
            # FK 순서를 신경 쓰지 않고 지우기 위해 잠시 끈다. 이 세션에만 적용된다.
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"DELETE FROM `{table.name}`"))
        if is_mysql:
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def new_session(engine: Engine) -> Session:
    return sessionmaker(bind=engine)()
