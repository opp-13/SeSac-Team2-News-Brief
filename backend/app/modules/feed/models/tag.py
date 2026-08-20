"""tags / user_tags 테이블 SQLAlchemy 모델.

컬럼 구성은 `docs/db/schema.sql`(V2)을 기준으로 맞췄다. 이전 정의는 `tags`에
`category` 문자열 컬럼을 두고 있었는데 스키마에는 없는 컬럼이라, MySQL에 스키마를
올리면 조회부터 실패했다. 스키마는 카테고리/키워드를 별도 컬럼이 아니라
`tag_type` ENUM으로 구분한다.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntType

# tags.tag_type ENUM 값. 카테고리 성격의 태그만 게스트 필터 칩에 노출된다.
TAG_TYPE_CATEGORY = "CATEGORY"
TAG_TYPE_KEYWORD = "KEYWORD"


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # ENUM('CATEGORY','KEYWORD'). 코드에 SQLAlchemy Enum으로 박지 않는다 — ENUM 값이 늘어날 때
    # 모델과 마이그레이션 양쪽을 고쳐야 하는 결합을 피한다.
    tag_type: Mapped[str] = mapped_column(String(20), nullable=False, default=TAG_TYPE_KEYWORD)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserTag(Base):
    __tablename__ = "user_tags"
    __table_args__ = (UniqueConstraint("user_id", "tag_id", name="uk_user_tags"),)

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    # 큐레이션 가중치 1~10 (schema.sql).
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
