"""데이터 보관 정책 배치 (C 소유 파일). 실행기 비의존."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.common.batch_log import finish_job, log_error, start_job
from app.modules.feed.services.retention_service import RetentionResult, run_retention

JOB_NAME = "retention"


def run(
    db: Session,
    *,
    retention_days: int | None = None,
    dry_run: bool = False,
    task_ref: str | None = None,
) -> RetentionResult:
    job_id = start_job(db, job_name=JOB_NAME, task_ref=task_ref, started_at=datetime.now(timezone.utc))
    try:
        kwargs = {"dry_run": dry_run}
        if retention_days is not None:
            kwargs["retention_days"] = retention_days
        result = run_retention(db, **kwargs)
        finish_job(
            db,
            job_id=job_id,
            status="SUCCESS",
            detail={
                "cutoff": result.cutoff.isoformat(),
                "deleted_feed_items": result.deleted_feed_items,
                "dry_run": result.dry_run,
            },
        )
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        log_error(db, job_id=job_id, error_code="RETENTION_FAILED", message=str(exc))
        finish_job(db, job_id=job_id, status="FAILED")
        db.commit()
        raise
