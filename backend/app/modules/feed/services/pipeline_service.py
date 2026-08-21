"""배치 실행 이력 조회 (docs/api-contracts/admin.md §1).

**"실행 1건 = 여러 단계" 모델이 스키마에 없다.** `batch_jobs`는 각 행이 곧 하나의 단계다
(job_type ENUM). 여러 단계를 묶는 부모 run 테이블을 새로 만드는 대신, 계약이 제안한 (a)안을
따른다 — **같은 날짜 · 같은 slot의 행들을 하나의 run으로 집계**한다. "하루 3회 고정 배치"라는
요구사항과 `slot` ENUM이 정확히 대응하므로 스키마를 늘리지 않고도 자연스럽게 묶인다.

run id는 `20260821-0700` 처럼 날짜+slot으로 합성한다. 이 값은 저장되지 않고 매번 계산된다 —
같은 정보를 두 곳에 두면 어긋나기 때문이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestError
from app.common.models.batch_job import BatchJob, JobLog
from app.modules.feed.services import cursor as cursor_codec

VALID_SLOTS = ("0700", "1200", "1700", "MANUAL")
VALID_LEVELS = ("INFO", "WARN", "ERROR")


@dataclass
class PipelineRun:
    id: str
    slot: str
    status: str
    executed_at: datetime | None
    processed_count: int
    error_count: int
    stages: list[BatchJob] = field(default_factory=list)


def _ts():
    """정렬·그룹핑 기준 시각.

    `started_at`은 nullable이다(아직 시작하지 않은 PENDING 행). 그 행이 그룹에서 통째로
    빠지지 않도록 `created_at`으로 떨어뜨린다.
    """
    return func.coalesce(BatchJob.started_at, BatchJob.created_at)


def _as_date(value) -> date:  # noqa: ANN001
    """`func.date()`의 반환 타입이 드라이버마다 다르다 — MySQL은 date, SQLite는 문자열.

    두 모드로 테스트를 돌리므로(CLAUDE.md §2.1) 여기서 한 형태로 맞춘다.
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


def run_id_of(day: date, slot: str) -> str:
    return f"{day.strftime('%Y%m%d')}-{slot}"


def parse_run_id(run_id: str) -> tuple[date, str]:
    """`20260821-0700` → (date(2026,8,21), '0700').

    slot에 하이픈이 없으므로 첫 하이픈에서 한 번만 자른다. 형식이 어긋나면 404가 아니라
    400이다 — 존재하지 않는 실행이 아니라 **id 자체가 잘못된 요청**이기 때문이다.
    """
    head, _, slot = run_id.partition("-")
    if len(head) != 8 or not head.isdigit() or slot not in VALID_SLOTS:
        raise BadRequestError("INVALID_RUN_ID")
    try:
        day = date(int(head[:4]), int(head[4:6]), int(head[6:8]))
    except ValueError as exc:
        raise BadRequestError("INVALID_RUN_ID") from exc
    return day, slot


def aggregate_status(statuses: list[str]) -> str:
    """단계 상태들로 run 상태를 정한다 (계약 §1 "run 단위 status 집계 규칙").

    스키마 ENUM 값을 대문자 그대로 쓴다 — 프런트 프로토타입이 쓰던 소문자로 바꾸면
    진실 공급원이 둘이 된다.
    """
    if not statuses:
        return "PENDING"
    if "RUNNING" in statuses:
        return "RUNNING"
    if all(s == "PENDING" for s in statuses):
        return "PENDING"
    if all(s == "SUCCESS" for s in statuses):
        return "SUCCESS"
    # 성공한 단계가 하나도 없으면 실패다. 계약의 "핵심 단계 실패로 후속이 모두 건너뜀"이
    # 이 경우에 해당한다.
    if not any(s in ("SUCCESS", "PARTIAL") for s in statuses):
        return "FAILED"
    return "PARTIAL"


def _grouped_stmt() -> Select:
    day = func.date(_ts()).label("day")
    return (
        select(
            day,
            BatchJob.slot.label("slot"),
            func.min(_ts()).label("executed_at"),
            # 합이 아니라 **최댓값**이다. 세 단계(COLLECT/SUMMARIZE/TRANSLATE)가 모두
            # 같은 기사를 세므로 합하면 3배가 된다(기사 4건 → "처리 12건"). 한 실행이
            # 다룬 기사 수는 가장 많이 처리한 단계의 수다. 뒤 단계는 앞 단계의 결과에서
            # 줄어들 뿐 늘지 않는다.
            func.max(BatchJob.success_count).label("processed"),
            func.sum(BatchJob.fail_count).label("errors"),
        )
        .group_by(day, BatchJob.slot)
        .order_by(func.min(_ts()).desc())
    )


def list_runs(
    db: Session, *, limit: int = 20, cursor: str | None = None
) -> tuple[list[PipelineRun], str | None, bool]:
    stmt = _grouped_stmt()

    cursor_ts: datetime | None = None
    cursor_key: str | None = None
    if cursor:
        cursor_ts, cursor_key = cursor_codec.decode_run(cursor)
        # `<` 가 아니라 `<=` 로 걸러 낸 뒤 파이썬에서 커서 자신을 떨군다. 서로 다른
        # (날짜, slot) 그룹이 초 단위까지 같은 executed_at을 갖는 일은 사실상 없지만,
        # 그 경우에 run 하나가 조용히 건너뛰어지는 것을 막는다.
        stmt = stmt.having(func.min(_ts()) <= cursor_ts)

    # 커서와 같은 시각의 행이 최대 1개 더 딸려올 수 있어 +2를 읽는다(+1은 has_next 판별용).
    rows = list(db.execute(stmt.limit(limit + 2)).all())

    runs: list[tuple[date, str, datetime, int, int]] = []
    for row in rows:
        day = _as_date(row.day)
        key = run_id_of(day, row.slot)
        executed_at = row.executed_at
        if cursor_ts is not None and executed_at == cursor_ts and key >= (cursor_key or ""):
            continue
        runs.append((day, row.slot, executed_at, int(row.processed or 0), int(row.errors or 0)))

    has_next = len(runs) > limit
    runs = runs[:limit]
    if not runs:
        return [], None, False

    stages_by_key = _load_stages(db, runs)

    result = [
        PipelineRun(
            id=run_id_of(day, slot),
            slot=slot,
            status=aggregate_status(
                [s.status for s in stages_by_key.get(run_id_of(day, slot), [])]
            ),
            executed_at=executed_at,
            processed_count=processed,
            error_count=errors,
            stages=stages_by_key.get(run_id_of(day, slot), []),
        )
        for day, slot, executed_at, processed, errors in runs
    ]

    last = runs[-1]
    next_cursor = (
        cursor_codec.encode_run(last[2], run_id_of(last[0], last[1])) if has_next else None
    )
    return result, next_cursor, has_next


def _load_stages(db: Session, runs: list[tuple]) -> dict[str, list[BatchJob]]:
    """페이지에 있는 run들의 단계를 한 번에 읽는다 (run마다 조회하면 N+1이다).

    `(날짜, slot)` 튜플 IN은 드라이버마다 지원이 갈려서, 날짜 범위 + slot 집합으로 넉넉히
    읽은 뒤 파이썬에서 정확한 키로 나눈다. 한 페이지는 20건 남짓이라 과다 조회가 아니다.
    """
    days = [r[0] for r in runs]
    slots = {r[1] for r in runs}
    wanted = {run_id_of(r[0], r[1]) for r in runs}

    rows = db.scalars(
        select(BatchJob)
        .where(
            func.date(_ts()) >= min(days),
            func.date(_ts()) <= max(days),
            BatchJob.slot.in_(slots),
        )
        .order_by(_ts().asc(), BatchJob.id.asc())
    ).all()

    grouped: dict[str, list[BatchJob]] = {}
    for job in rows:
        key = run_id_of(_as_date(job.started_at or job.created_at), job.slot)
        if key in wanted:
            grouped.setdefault(key, []).append(job)
    return grouped


def list_run_logs(
    db: Session, *, run_id: str, level: str | None = None
) -> list[tuple[JobLog, str]]:
    """한 실행의 로그를 `(로그, job_type)` 쌍으로 돌려준다. `level`을 생략하면 전체.

    run은 집계 개념이라 `job_logs`에 run 컬럼이 없다 — 해당 run에 속한 `batch_jobs`를
    조인해서 그 job들의 로그를 읽는다. 로그마다 job을 다시 조회하면 N+1이 되므로
    `job_type`을 같은 쿼리에서 함께 가져온다.
    """
    day, slot = parse_run_id(run_id)
    if level is not None and level not in VALID_LEVELS:
        raise BadRequestError("INVALID_LOG_LEVEL")

    stmt = (
        select(JobLog, BatchJob.job_type)
        .join(BatchJob, BatchJob.id == JobLog.job_id)
        .where(func.date(_ts()) == day, BatchJob.slot == slot)
        .order_by(JobLog.created_at.desc(), JobLog.id.desc())
    )
    if level is not None:
        stmt = stmt.where(JobLog.level == level)
    return [(log, job_type) for log, job_type in db.execute(stmt).all()]
