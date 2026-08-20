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
    article_retention_days: int | None = None,
    dry_run: bool = False,
    task_ref: str | None = None,
) -> RetentionResult:
    """보관 배치 엔트리.

    `article_retention_days`를 주지 않으면 서비스의 기본값(원문 hard delete 포함)이 쓰인다.
    원문 정리를 건너뛰려면 `article_retention_days=None`이 아니라 서비스를 직접 호출한다 —
    여기서는 "값을 안 줬다"와 "끄고 싶다"를 구분하지 않는다.
    """
    job_id = start_job(db, job_name=JOB_NAME, task_ref=task_ref, started_at=datetime.now(timezone.utc))
    try:
        kwargs = {"dry_run": dry_run}
        if retention_days is not None:
            kwargs["retention_days"] = retention_days
        if article_retention_days is not None:
            kwargs["article_retention_days"] = article_retention_days
        result = run_retention(db, **kwargs)
        finish_job(
            db,
            job_id=job_id,
            status="SUCCESS",
            detail={
                "feed_item_cutoff": result.feed_item_cutoff.isoformat(),
                "article_cutoff": result.article_cutoff.isoformat(),
                "deleted_feed_items": result.deleted_feed_items,
                # 되돌릴 수 없는 삭제다. 요약/원문 건수는 반드시 남긴다 (CLAUDE.md §9).
                "deleted_summaries": result.deleted_summaries,
                "deleted_articles": result.deleted_articles,
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
