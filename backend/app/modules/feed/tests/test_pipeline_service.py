"""배치 실행 이력: run 묶기 · 상태 집계 · 커서.

`batch_jobs`는 각 행이 하나의 **단계**라 "실행 1건"이라는 개념이 테이블에 없다.
그 묶는 규칙(같은 날짜 + 같은 slot)이 이 모듈의 핵심이라 여기서 고정한다.
"""

from datetime import date, datetime, timedelta

import pytest

from app.common.exceptions import BadRequestError
from app.common.models.batch_job import BatchJob, JobLog
from app.modules.feed.services import pipeline_service as ps

BASE = datetime(2026, 8, 21, 7, 0)


def _job(db, *, job_type, slot, status, minutes=0, success=0, fail=0, target=0):
    job = BatchJob(
        job_type=job_type,
        slot=slot,
        status=status,
        target_count=target,
        success_count=success,
        fail_count=fail,
        started_at=BASE + timedelta(minutes=minutes),
        finished_at=BASE + timedelta(minutes=minutes + 1),
    )
    db.add(job)
    db.flush()
    return job


# ── 상태 집계 (계약 §1) ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "statuses,expected",
    [
        (["SUCCESS", "SUCCESS"], "SUCCESS"),
        (["SUCCESS", "RUNNING"], "RUNNING"),      # 실행 중이 최우선
        (["PENDING", "PENDING"], "PENDING"),
        (["SUCCESS", "FAILED"], "PARTIAL"),
        (["PARTIAL"], "PARTIAL"),
        (["FAILED", "FAILED"], "FAILED"),
        (["FAILED", "PENDING"], "FAILED"),        # 후속이 건너뛰어진 경우
        ([], "PENDING"),
    ],
)
def test_status_aggregation(statuses, expected):
    assert ps.aggregate_status(statuses) == expected


# ── run id 파싱 ───────────────────────────────────────────────────────

def test_run_id_roundtrip():
    for slot in ("0700", "1200", "1700", "MANUAL"):
        rid = ps.run_id_of(date(2026, 8, 21), slot)
        assert ps.parse_run_id(rid) == (date(2026, 8, 21), slot)


@pytest.mark.parametrize("bad", ["bogus", "2026821-0700", "20260821-9999", "20260899-0700", ""])
def test_malformed_run_id_is_rejected(bad):
    """실패 경로: 형식이 틀리면 404가 아니라 400이다 — 없는 실행이 아니라 잘못된 요청이다."""
    with pytest.raises(BadRequestError):
        ps.parse_run_id(bad)


# ── run 묶기 ──────────────────────────────────────────────────────────

def test_same_day_and_slot_becomes_one_run(db, seed):
    """같은 날짜·같은 slot의 단계들이 실행 1건으로 묶인다."""
    _job(db, job_type="COLLECT", slot="0700", status="SUCCESS", minutes=0, success=10)
    _job(db, job_type="FEED", slot="0700", status="SUCCESS", minutes=30, success=5)
    db.flush()

    runs, _, _ = ps.list_runs(db, limit=10)
    run = next(r for r in runs if r.id == "20260821-0700")

    assert [s.job_type for s in run.stages] == ["COLLECT", "FEED"]
    # 합(15)이 아니라 최댓값. 단계들이 같은 기사를 세므로 합하면 부풀려진다.
    assert run.processed_count == 10
    assert run.status == "SUCCESS"


def test_different_slots_are_separate_runs(db, seed):
    """같은 날이라도 slot이 다르면 별개의 실행이다."""
    _job(db, job_type="COLLECT", slot="0700", status="SUCCESS", minutes=0)
    _job(db, job_type="COLLECT", slot="1200", status="FAILED", minutes=300)
    db.flush()

    runs, _, _ = ps.list_runs(db, limit=10)
    ids = {r.id for r in runs}

    assert {"20260821-0700", "20260821-1200"} <= ids
    assert next(r for r in runs if r.id == "20260821-1200").status == "FAILED"


def test_runs_are_newest_first(db, seed):
    """최신 실행이 먼저 온다."""
    _job(db, job_type="COLLECT", slot="0700", status="SUCCESS", minutes=0)
    _job(db, job_type="COLLECT", slot="1700", status="SUCCESS", minutes=600)
    db.flush()

    runs, _, _ = ps.list_runs(db, limit=10)
    ids = [r.id for r in runs]

    assert ids.index("20260821-1700") < ids.index("20260821-0700")


def test_cursor_walks_without_gaps_or_repeats(db, seed):
    """커서로 이어 읽어도 빠지거나 겹치는 실행이 없다."""
    for i, slot in enumerate(("0700", "1200", "1700")):
        _job(db, job_type="COLLECT", slot=slot, status="SUCCESS", minutes=i * 300)
    db.flush()

    seen: list[str] = []
    cursor = None
    for _ in range(10):
        runs, cursor, has_next = ps.list_runs(db, limit=1, cursor=cursor)
        seen.extend(r.id for r in runs)
        if not has_next:
            break

    assert len(seen) == len(set(seen))
    assert {"20260821-0700", "20260821-1200", "20260821-1700"} <= set(seen)


def test_malformed_cursor_is_rejected(db, seed):
    """실패 경로: 깨진 커서는 피드와 같은 INVALID_CURSOR로 거부한다."""
    with pytest.raises(BadRequestError):
        ps.list_runs(db, limit=10, cursor="!!not-a-cursor!!")


# ── 로그 ──────────────────────────────────────────────────────────────

def test_run_logs_are_scoped_to_that_run(db, seed):
    """다른 실행의 로그가 섞이지 않는다."""
    mine = _job(db, job_type="COLLECT", slot="0700", status="PARTIAL", minutes=0)
    other = _job(db, job_type="COLLECT", slot="1700", status="SUCCESS", minutes=600)
    db.add(JobLog(job_id=mine.id, level="ERROR", error_code="COLLECT_FAILED", message="내 것"))
    db.add(JobLog(job_id=other.id, level="ERROR", error_code="COLLECT_FAILED", message="남의 것"))
    db.flush()

    logs = ps.list_run_logs(db, run_id="20260821-0700")

    assert [log.message for log, _ in logs] == ["내 것"]
    assert [job_type for _, job_type in logs] == ["COLLECT"]


def test_run_logs_filter_by_level(db, seed):
    """level을 주면 그 등급만, 생략하면 전체."""
    job = _job(db, job_type="COLLECT", slot="0700", status="PARTIAL", minutes=0)
    db.add(JobLog(job_id=job.id, level="INFO", message="정보"))
    db.add(JobLog(job_id=job.id, level="ERROR", error_code="X", message="오류"))
    db.flush()

    assert len(ps.list_run_logs(db, run_id="20260821-0700")) == 2
    errors = ps.list_run_logs(db, run_id="20260821-0700", level="ERROR")
    assert [log.message for log, _ in errors] == ["오류"]


def test_unknown_log_level_is_rejected(db, seed):
    """실패 경로: 스키마 ENUM에 없는 level은 조용히 무시하지 않고 거부한다."""
    with pytest.raises(BadRequestError):
        ps.list_run_logs(db, run_id="20260821-0700", level="TRACE")


def test_processed_count_is_not_summed_across_stages(db, seed):
    """회귀 방지: 단계 성공 건수를 합하면 같은 기사를 여러 번 센다.

    수집기가 COLLECT/SUMMARIZE/TRANSLATE를 각각 남기면서 셋 다 같은 기사를 센다.
    기사 4건을 처리한 실행이 "처리 12건"으로 보이던 문제.
    """
    for job_type in ("COLLECT", "SUMMARIZE", "TRANSLATE"):
        _job(db, job_type=job_type, slot="0700", status="SUCCESS", success=4, target=4)
    db.flush()

    runs, _, _ = ps.list_runs(db, limit=10)
    run = next(r for r in runs if r.id == "20260821-0700")

    assert run.processed_count == 4  # 12이 아니다
