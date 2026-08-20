"""users 테이블 SQLAlchemy 모델.

[SCHEMA-CHECK] 컬럼 구성은 `docs/db/schema.sql`(V1.1)을 기준으로 확정해야 한다.
아래는 CLAUDE.md에 언급된 컬럼(users.preferred_language 등) 기반의 임시 정의이며,
schema.sql과 다르면 **모델을 schema.sql에 맞춘다.** 마이그레이션은 임의 생성하지 않는다.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base  # 공용(shared) — C가 수정하지 않는다


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    # [OPEN] 허용 값은 미결 사항(B·C 협의). 코드에 Enum으로 박지 않는다.
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="ko")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
