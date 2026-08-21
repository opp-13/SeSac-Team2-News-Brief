"""배치 실행 이력 기록 (`batch_jobs` / `job_logs`).

수집기는 지금까지 실행 이력을 한 줄도 남기지 않았다. 그래서 관리자 파이프라인 화면이
`COLLECT` 한 덩어리만 보여주고 그 안에서 요약·번역이 몇 건 실패했는지는 알 수 없었다
(`docs/api-contracts/admin.md` §1 "열려있는 질문" 14번).

**한 실행 = 한 단계당 한 행.** CLI는 카테고리마다 따로 실행되므로(슬롯당 21회), 실행마다
행을 만들면 슬롯 하나에 63행이 쌓여 화면이 못 쓰게 된다. `task_ref`를
`{stage}:{slot}:{날짜}`로 잡고 **같은 행에 누적**한다. `batch_jobs.task_ref` UNIQUE가
그 합류점을 보장한다.

**실행기에 결합하지 않는다** (CLAUDE.md §2). 슬롯·날짜는 환경변수로 주입받고, 없으면
`MANUAL` + 오늘로 떨어진다 — CLI를 손으로 돌려도 그대로 동작한다.

MySQL 8.0.19+ 의 행 별칭 문법(`AS new`)을 쓴다. `VALUES()`는 8.0.20에서 deprecated 됐다.
"""

import os
import sys
from datetime import date

VALID_SLOTS = ("0700", "1200", "1700", "MANUAL")

# batch_jobs.job_type ENUM 중 수집기가 남기는 것들
COLLECT = "COLLECT"
SUMMARIZE = "SUMMARIZE"
TRANSLATE = "TRANSLATE"


def resolve_run() -> tuple[str, date]:
    """이번 실행이 속한 (slot, 날짜).

    스케줄러가 `BATCH_SLOT` / `BATCH_DATE`를 넣어 준다. 손으로 돌릴 때는 비어 있으므로
    MANUAL + 오늘로 본다 — 그래야 같은 날 수동 실행이 한 행에 모인다.
    """
    slot = os.environ.get("BATCH_SLOT", "").strip() or "MANUAL"
    if slot not in VALID_SLOTS:
        print(f"[batch_log] 알 수 없는 BATCH_SLOT={slot!r} → MANUAL로 기록", file=sys.stderr)
        slot = "MANUAL"

    raw = os.environ.get("BATCH_DATE", "").strip()
    if not raw:
        return slot, date.today()
    try:
        return slot, date.fromisoformat(raw)
    except ValueError:
        print(f"[batch_log] 알 수 없는 BATCH_DATE={raw!r} → 오늘로 기록", file=sys.stderr)
        return slot, date.today()


def task_ref(job_type: str, slot: str, day: date) -> str:
    return f"{job_type.lower()}:{slot}:{day.isoformat()}"


def _status_for(success: int, fail: int) -> str:
    if fail and not success:
        return "FAILED"
    if fail:
        return "PARTIAL"
    return "SUCCESS"


def record_stage(
    cursor,
    *,
    job_type: str,
    slot: str,
    day: date,
    target: int = 0,
    success: int = 0,
    fail: int = 0,
) -> int:
    """단계 결과를 누적하고 `batch_jobs.id`를 돌려준다.

    status를 카운트보다 **먼저** 갱신한다 — MySQL은 ON DUPLICATE KEY UPDATE 절을 왼쪽부터
    평가하므로, 카운트를 먼저 더하면 status가 새 값을 보고 계산돼 이번 호출분이 두 번
    반영된다. 지금 순서라야 "기존값 + 이번 증가분"으로 한 번만 센다.
    """
    ref = task_ref(job_type, slot, day)
    cursor.execute(
        """
        INSERT INTO batch_jobs
            (job_type, slot, task_ref, status,
             target_count, success_count, fail_count, started_at, finished_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW()) AS new
        ON DUPLICATE KEY UPDATE
            status = CASE
                WHEN batch_jobs.success_count + new.success_count = 0
                     AND batch_jobs.fail_count + new.fail_count > 0 THEN 'FAILED'
                WHEN batch_jobs.fail_count + new.fail_count > 0 THEN 'PARTIAL'
                ELSE 'SUCCESS'
            END,
            target_count  = batch_jobs.target_count  + new.target_count,
            success_count = batch_jobs.success_count + new.success_count,
            fail_count    = batch_jobs.fail_count    + new.fail_count,
            finished_at   = NOW(),
            id = LAST_INSERT_ID(batch_jobs.id)
        """,
        (job_type, slot, ref, _status_for(success, fail), target, success, fail),
    )
    return cursor.lastrowid


def log(
    cursor,
    *,
    job_id: int,
    level: str,
    message: str,
    error_code: str | None = None,
    article_id: int | None = None,
) -> None:
    """`job_logs`에 한 줄 남긴다. 실패 원인은 stderr가 아니라 여기에 남아야 화면에 뜬다.

    message는 TEXT지만 스택 트레이스가 통째로 들어오면 화면에서 읽을 수 없으므로 자른다.
    """
    cursor.execute(
        """
        INSERT INTO job_logs (job_id, article_id, level, error_code, message)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (job_id, article_id, level, error_code, (message or "")[:1000]),
    )
