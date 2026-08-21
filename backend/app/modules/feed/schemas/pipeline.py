"""배치 실행 이력 응답 스키마 (docs/api-contracts/admin.md §1).

DB 컬럼을 그대로 흘려보내지 않는다 — 계약 형태로 여기서 변환한다 (SKILL §3).
"""

from datetime import datetime

from app.modules.feed.schemas.base import ApiModel


class PipelineStageResponse(ApiModel):
    """실행 1건을 이루는 단계 하나 = `batch_jobs` 행 하나."""

    job_type: str
    status: str
    target_count: int
    success_count: int
    fail_count: int
    started_at: datetime | None
    finished_at: datetime | None


class PipelineRunResponse(ApiModel):
    """같은 날짜·같은 slot의 `batch_jobs` 행들을 하나로 묶은 실행."""

    id: str
    slot: str
    status: str
    executed_at: datetime | None
    processed_count: int
    error_count: int
    stages: list[PipelineStageResponse]


class PipelineRunListResponse(ApiModel):
    runs: list[PipelineRunResponse]
    next_cursor: str | None
    has_next: bool


class JobLogResponse(ApiModel):
    id: str  # BIGINT는 JS 안전 정수를 넘을 수 있어 문자열로 (계약 공통 규약)
    job_type: str
    article_id: str | None
    level: str
    error_code: str | None
    message: str | None
    retry_count: int
    created_at: datetime


class JobLogListResponse(ApiModel):
    logs: list[JobLogResponse]
