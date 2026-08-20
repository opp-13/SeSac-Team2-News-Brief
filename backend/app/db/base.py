"""SQLAlchemy declarative base (공용 영역).

모든 모듈의 모델이 이 Base를 상속한다. 모델 파일은 도메인별로 분리하고 단일
`models.py`를 만들지 않는다 (CLAUDE.md §7).

주의: `Base.metadata.create_all()`은 테스트(SQLite in-memory)에서만 쓴다. 운영 스키마의
기준은 `docs/db/schema.sql`이고 변경은 Alembic + C 창구를 거친다 (§5 규칙 6).
"""

from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# MySQL에서는 BIGINT, SQLite에서는 INTEGER로 매핑되는 타입.
#
# 왜 필요한가: 스키마의 PK 다수가 `BIGINT UNSIGNED`인데, SQLite는 `INTEGER PRIMARY KEY`
# 만 rowid 별칭으로 취급해 자동 증가시킨다. `BIGINT PRIMARY KEY`로 두면 INSERT 시
# "NOT NULL constraint failed: <table>.id"로 깨진다. 테스트는 SQLite in-memory로
# 돌아가므로(각 모듈 tests/conftest.py) 그대로 두면 테스트에서만 실패한다.
#
# BIGINT 컬럼(PK·FK 모두)에는 Integer/BigInteger 대신 이 타입을 쓴다.
BigIntType = BigInteger().with_variant(Integer, "sqlite")
