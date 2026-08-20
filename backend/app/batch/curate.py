"""큐레이션 배치 (C 소유 파일).

**실행기 비의존**: 스케줄러/큐 데코레이터를 붙이지 않는다. 트리거는 기술 확정 후
별도 계층에서 이 함수를 호출한다 (CLAUDE.md §2).
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.common.batch_log import finish_job, log_error, start_job  # 공용 — 수정하지 않음
from app.modules.feed.services.curation_service import CurationResult, run_curation

JOB_NAME = "curate"


def run(db: Session, *, article_limit: int = 200, task_ref: str | None = None) -> CurationResult:
    """배치 엔트리 함수. 실행 이력은 batch_jobs, 오류는 job_logs에 기록한다."""
    job_id = start_job(db, job_name=JOB_NAME, task_ref=task_ref, started_at=datetime.now(timezone.utc))
    try:
        result = run_curation(db, article_limit=article_limit)
        finish_job(
            db,
            job_id=job_id,
            status="SUCCESS",
            detail={
                "scanned_users": result.scanned_users,
                "created_items": result.created_items,
                "skipped_no_summary": result.skipped_no_summary,
                "skipped_duplicate": result.skipped_duplicate,
            },
        )
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        log_error(db, job_id=job_id, error_code="CURATION_FAILED", message=str(exc))
        finish_job(db, job_id=job_id, status="FAILED")
        db.commit()
        raise
