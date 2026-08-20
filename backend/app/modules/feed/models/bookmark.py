"""북마크 모델.

[SCHEMA-CHECK] `bookmarks` 테이블이 V1.1 스키마에 없다면 **코드를 먼저 쓰지 말고**
스키마 변경안을 사용자에게 보고한 뒤 C 창구로 revision을 만든다 (SKILL §5).
현재는 계약/스키마 확정 전 임시 정의다.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "feed_item_id", name="uq_bookmarks_user_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    feed_item_id: Mapped[int] = mapped_column(ForeignKey("feed_items.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
