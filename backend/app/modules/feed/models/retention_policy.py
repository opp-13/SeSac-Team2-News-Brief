"""retention_policies 테이블 모델 (C 소유).

보관 정책은 관리자 화면에서 수정하고 보관 배치가 읽는다. 이전에는 배치가 코드 상수를
썼기 때문에 화면에서 기간을 바꿔도 배치에 반영되지 않았다.

`target_entity`가 `uk_retention_target`으로 유일하므로 그 값이 곧 식별자다
(`docs/api-contracts/admin.md`).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# target_entity ENUM. 값이 곧 API의 식별자이므로 상수로 고정한다.
# INVOCATIONS는 비용 추적을 스코프에서 빼면서 제거했다 (리비전 0003_drop_cost).
TARGET_ARTICLES = "ARTICLES"
TARGET_SUMMARIES = "SUMMARIES"
TARGET_TRANSLATIONS = "TRANSLATIONS"
TARGET_FEED_ITEMS = "FEED_ITEMS"
TARGET_LOGS = "LOGS"

TARGET_ENTITIES = (
    TARGET_ARTICLES,
    TARGET_SUMMARIES,
    TARGET_TRANSLATIONS,
    TARGET_FEED_ITEMS,
    TARGET_LOGS,
)


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_entity: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # V2에서 PARTITION_DROP을 뺐으므로 실질적으로 단일값이다. 화면에는 노출하지 않는다.
    strategy: Mapped[str] = mapped_column(String(20), nullable=False, default="BATCH_DELETE")
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
