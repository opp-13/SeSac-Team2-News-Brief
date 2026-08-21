"""관리자 배치 실행 이력 라우터.

로직은 services에 둔다 — 여기는 입출력과 의존성 주입만 (SKILL §4-4).
"""

from fastapi import APIRouter, Depends, Query

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_admin
from app.modules.auth.models.user import User
from app.modules.feed import api_paths
from app.modules.feed.schemas.pipeline import (
    JobLogListResponse,
    JobLogResponse,
    PipelineRunListResponse,
    PipelineRunResponse,
    PipelineStageResponse,
)
from app.modules.feed.services import pipeline_service

pipeline_router = APIRouter(
    prefix=api_paths.ADMIN_PIPELINE_PREFIX, tags=["admin-pipeline"]
)


@pipeline_router.get(api_paths.ADMIN_PIPELINE_RUNS, response_model=PipelineRunListResponse)
def list_pipeline_runs(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    _admin: User = Depends(get_current_admin),
    db=Depends(get_db),
) -> PipelineRunListResponse:
    runs, next_cursor, has_next = pipeline_service.list_runs(db, limit=limit, cursor=cursor)
    return PipelineRunListResponse(
        runs=[
            PipelineRunResponse(
                id=r.id,
                slot=r.slot,
                status=r.status,
                executed_at=r.executed_at,
                processed_count=r.processed_count,
                error_count=r.error_count,
                stages=[
                    PipelineStageResponse(
                        job_type=s.job_type,
                        status=s.status,
                        target_count=s.target_count,
                        success_count=s.success_count,
                        fail_count=s.fail_count,
                        started_at=s.started_at,
                        finished_at=s.finished_at,
                    )
                    for s in r.stages
                ],
            )
            for r in runs
        ],
        next_cursor=next_cursor,
        has_next=has_next,
    )


@pipeline_router.get(api_paths.ADMIN_PIPELINE_RUN_LOGS, response_model=JobLogListResponse)
def list_pipeline_run_logs(
    run_id: str,
    level: str | None = None,
    _admin: User = Depends(get_current_admin),
    db=Depends(get_db),
) -> JobLogListResponse:
    rows = pipeline_service.list_run_logs(db, run_id=run_id, level=level)
    return JobLogListResponse(
        logs=[
            JobLogResponse(
                # BIGINT를 그대로 내보내면 JS 안전 정수 범위를 넘을 수 있다 (계약 공통 규약).
                id=str(log.id),
                job_type=job_type,
                article_id=str(log.article_id) if log.article_id is not None else None,
                level=log.level,
                error_code=log.error_code,
                message=log.message,
                retry_count=log.retry_count,
                created_at=log.created_at,
            )
            for log, job_type in rows
        ]
    )
