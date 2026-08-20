"""feed_items 모델.

**이 테이블의 INSERT 소유자는 C뿐이다** (CLAUDE.md §8-5). B는 summaries/translations까지만 쓴다.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeedItem(Base):
    __tablename__ = "feed_items"
    __table_args__ = (
        # 같은 사용자에게 같은 기사가 중복 노출되지 않도록 보증한다.
        UniqueConstraint("user_id", "article_id", name="uq_feed_items_user_article"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # [SCHEMA-CHECK] articles 파티셔닝 여부 미결 → FK 유지 여부는 확정 후 조정 (CLAUDE.md §8 미결)
    article_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    summary_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    translation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_tag_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
