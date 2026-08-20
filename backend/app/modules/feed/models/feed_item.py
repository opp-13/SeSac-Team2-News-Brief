"""feed_items 테이블 SQLAlchemy 모델 (C 소유).

컬럼 구성은 `docs/db/schema.sql`(V2) 기준이다. 이전 정의에는 스키마에 없는
`language` 컬럼이 있었고 `score` / `is_read` / `is_bookmarked`가 빠져 있었다.

노출 언어는 별도 컬럼으로 두지 않는다 — `translation_id`가 있으면 그 번역의
`target_language`가, 없으면 원문(`articles.language`)이 노출 언어다. 같은 정보를
두 곳에 두면 어긋난다.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntType


class FeedItem(Base):
    __tablename__ = "feed_items"
    __table_args__ = (
        # 같은 사용자에게 같은 기사가 중복 노출되지 않도록 보증한다.
        UniqueConstraint("user_id", "article_id", name="uk_feed"),
    )

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # V2가 파티셔닝을 제거하면서 articles가 FK 대상이 될 수 있게 됐다.
    # RESTRICT인 이유: 원문 삭제로 피드 행이 조용히 사라지지 않게 한다. 피드는 summaries에서
    # curate 배치가 다시 만들 수 있으므로, 정리는 summaries 삭제(→ CASCADE) 경로로만 일어난다.
    article_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("articles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # 스키마상 NOT NULL이다 — 요약 없는 기사는 애초에 피드 행을 만들지 않는다(curation_service).
    summary_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("summaries.id", ondelete="CASCADE"), nullable=False
    )
    # 원문 언어와 노출 언어가 같으면 NULL이다.
    translation_id: Mapped[int | None] = mapped_column(
        BigIntType, ForeignKey("translations.id", ondelete="SET NULL"), nullable=True
    )
    # 이 기사가 노출된 사유. 태그가 지워지면 사유만 사라지고 피드 행은 남는다.
    matched_tag_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True
    )
    # 큐레이션 점수 (curate 배치가 채운다).
    score: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # [미사용] 북마크는 기능 범위에서 제외됐다 (design_plan.md §6.3 "공유·스크랩 넣지 않는다",
    # frontend/CLAUDE.md §0.2). 스키마에 컬럼이 남아 있어 모델에는 선언해 두지만 아무도 쓰지 않는다.
    # 컬럼 제거는 스키마 변경이라 C 창구를 거쳐야 한다 (CLAUDE.md §5 규칙 5).
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
