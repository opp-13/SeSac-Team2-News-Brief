"""보관 정책 응답/요청 스키마 (`docs/api-contracts/admin.md`)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.feed.schemas.base import ApiModel


class RetentionPolicyResponse(ApiModel):
    target_entity: str
    retention_days: int
    strategy: str
    is_active: bool
    # 스키마에 없는 파생값 — 대상 테이블의 현재 행 수.
    record_count: int
    last_executed_at: datetime | None = None


class RetentionPolicyUpdateRequest(BaseModel):
    """부분 수정. 화면이 편집할 수 있는 값은 이 둘뿐이다(strategy는 화면에 없음)."""

    retention_days: int | None = Field(default=None, alias="retentionDays")
    is_active: bool | None = Field(default=None, alias="isActive")

    model_config = {"populate_by_name": True}
