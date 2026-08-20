"""배치 실행 이력 기록 (공용 영역).

배치 결과는 print가 아니라 `batch_jobs` / `job_logs` 테이블에 남긴다 (CLAUDE.md §9).
호출 형태는 기존 배치 파일(`batch/curate.py`, `batch/retention.py`)에 맞췄다.

**커밋하지 않는다.** 호출한 배치가 `db.commit()` / `db.rollback()`을 직접 제어한다
(`curate.py`가 실패 시 rollback → log_error → finish_job → commit 순서로 쓴다).
여기서 커밋하면 그 흐름이 깨진다.

---
**결정 필요 2건** — 임의로 확정하지 않고 현재 동작만 적어둔다.

1. `job_name` → `batch_jobs.job_type` 매핑
   호출 측은 `"curate"` / `"retention"` 같은 배치 파일 이름을 넘기는데, 스키마 ENUM은
   `COLLECT / SUMMARIZE / TRANSLATE / FEED / RETENTION`이다. 아래 `_JOB_TYPES`로
   변환하고 있으며, 특히 **`curate` → `FEED`** 는 추측이다. C 확인이 필요하다.

2. `finish_job(detail=...)`을 어디에 쓰는지
   `batch_jobs`에 detail 컬럼이 없다. 지금은 `job_logs`에 INFO 한 줄로 JSON을 남긴다.
   `success_count` / `fail_count` 컬럼에 매핑하려면 detail의 키 이름이 배치마다 달라서
   (`created_items`, `deleted_rows` …) 공용 코드가 알 수 없다. 선택지는
   (a) 호출 측이 `success_count=` 를 명시적으로 넘기게 시그니처 확장,
   (b) `batch_jobs`에 JSON detail 컬럼 추가(스키마 변경 → C 창구),
   (c) 현재처럼 job_logs INFO 로 유지.
"""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.common.models.batch_job import BatchJob, JobLog

# 배치 파일 이름 → batch_jobs.job_type ENUM 값
_JOB_TYPES: dict[str, str] = {
    "collect": "COLLECT",
    "summarize": "SUMMARIZE",
    "translate": "TRANSLATE",
    "curate": "FEED",  # [확인 필요] 큐레이션이 ENUM 'FEED'에 해당하는지 C 확인
    "retention": "RETENTION",
}


def resolve_job_type(job_name: str) -> str:
    """이름을 ENUM 값으로 바꾼다. 모르는 이름은 대문자로 올려 그대로 시도한다 —
    조용히 다른 값으로 바꿔치기하면 집계가 틀어지므로 추측하지 않는다."""
    return _JOB_TYPES.get(job_name.lower(), job_name.upper())


def start_job(
    db: Session,
    *,
    job_name: str,
    task_ref: str | None = None,
    started_at: datetime | None = None,
    slot: str = "MANUAL",
    target_count: int = 0,
) -> int:
    """실행 시작을 기록하고 batch_jobs.id를 돌려준다."""
    job = BatchJob(
        job_type=resolve_job_type(job_name),
        slot=slot,
        task_ref=task_ref,
        status="RUNNING",
        target_count=target_count,
        started_at=started_at or datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()  # id를 즉시 얻기 위해 flush만 한다 (커밋은 호출 측 책임)
    return job.id


def finish_job(
    db: Session,
    *,
    job_id: int,
    status: str,
    detail: dict | None = None,
    success_count: int | None = None,
    fail_count: int | None = None,
) -> None:
    """실행 종료를 기록한다. status는 SUCCESS / PARTIAL / FAILED."""
    job = db.get(BatchJob, job_id)
    if job is None:
        # 이력 기록 실패가 배치 자체를 죽이면 안 된다. 로그만 남기고 넘어간다.
        db.add(
            JobLog(
                job_id=job_id,
                level="WARN",
                error_code="JOB_NOT_FOUND",
                message=f"finish_job: batch_jobs.id={job_id} 없음",
            )
        )
        return

    job.status = status
    job.finished_at = datetime.now(timezone.utc)
    if success_count is not None:
        job.success_count = success_count
    if fail_count is not None:
        job.fail_count = fail_count

    if detail:
        # 위 docstring "결정 필요 2번" 참고 — batch_jobs에 detail 컬럼이 없어 여기 남긴다.
        db.add(
            JobLog(
                job_id=job_id,
                level="INFO",
                error_code=None,
                message=json.dumps(detail, ensure_ascii=False, default=str),
            )
        )


def log_error(
    db: Session,
    *,
    job_id: int,
    error_code: str,
    message: str,
    article_id: int | None = None,
    retry_count: int = 0,
    level: str = "ERROR",
) -> None:
    """오류를 job_logs에 남긴다. 기사 단위 실패면 article_id를 함께 넘긴다."""
    db.add(
        JobLog(
            job_id=job_id,
            article_id=article_id,
            level=level,
            error_code=error_code,
            message=message,
            retry_count=retry_count,
        )
    )
