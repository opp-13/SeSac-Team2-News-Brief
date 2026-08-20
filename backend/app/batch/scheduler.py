"""배치 스케줄러 (C 소유).

`feature/feed/module-skeleton`의 `503aa3c`(Ryu-JaeHee)를 현재 공용 스켈레톤에 맞춰 가져왔다.
원본의 구조(슬롯 상수를 한 곳에 모으고 배치 로직은 run() 호출만)는 그대로 두고,
공용 인프라가 생기기 전이라 임시로 처리돼 있던 부분을 교체했다.

  - DB URL 하드코딩 → `app.core.config` (CLAUDE.md §7 시크릿 규칙)
  - 전용 세션 팩토리 → `app.db.session.SessionLocal`
  - 서비스 함수 직접 호출 → `app.batch.{curate,retention}.run` (실행 이력·오류 기록, §9)
  - `ret.deleted_items` → 보관 결과가 원문/요약/피드로 나뉜 뒤의 실제 필드명
  - 중복 실행 방지 추가 (아래)

[실행기 결합 규칙 — CLAUDE.md §2]
스케줄 시각은 설정(`batch_slots`)에서 읽고, 배치 로직은 각 모듈의 `run()`을 호출할 뿐이다.
이 파일에 비즈니스 로직을 쓰지 않는다. 스케줄러를 갈아끼우면 이 파일만 교체된다.

[중복 실행 방지]
APScheduler는 프로세스 안에서 돈다. uvicorn 워커가 둘이면 같은 슬롯이 두 번 실행된다.
보관 배치는 되돌릴 수 없는 삭제를 하므로 Redis 락으로 한 번만 돌게 막는다
(`lock:job:{job_type}:{slot}` — schema.sql 하단 Redis 키 설계).
락은 최종 방어가 아니라 1차 방어다. 최종 보증은 `batch_jobs.task_ref` UNIQUE다.
"""

import logging
from datetime import date

import httpx
import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.batch import curate, retention
from app.core.config import get_settings
from app.core.redis import _pool
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# 락 TTL. 배치가 이보다 오래 걸리면 두 번째 실행이 들어올 수 있으므로 넉넉히 잡는다.
_LOCK_TTL_SECONDS = 30 * 60


def _slot_to_time(slot: str) -> tuple[int, int]:
    """'0700' → (7, 0). 설정값이 곧 스케줄 시각이다."""
    return int(slot[:2]), int(slot[2:])


def _acquire_lock(client: redis.Redis, job_type: str, slot: str) -> bool:
    """오늘 이 슬롯을 아직 아무도 실행하지 않았으면 True.

    날짜를 키에 넣어 매일 새로 시작한다. `nx=True`라 먼저 잡은 프로세스만 통과한다.
    """
    key = f"lock:job:{job_type}:{slot}:{date.today().isoformat()}"
    return bool(client.set(key, "1", nx=True, ex=_LOCK_TTL_SECONDS))


async def trigger_collect(slot: str) -> None:
    """A+B 수집·요약 파이프라인을 HTTP로 깨운다.

    엔드포인트가 아직 없으므로(설정 미지정) 기본은 건너뛴다. A가 경로를 확정하면
    `COLLECT_TRIGGER_URL` 설정만 채우면 된다 — 이 파일은 고치지 않는다.
    """
    settings = get_settings()
    url = settings.collect_trigger_url
    if not url:
        logger.info("[scheduler] collect 트리거 건너뜀 — COLLECT_TRIGGER_URL 미설정 (slot=%s)", slot)
        return

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={"slot": slot})
            resp.raise_for_status()
        logger.info("[scheduler] collect 트리거 성공 — slot=%s status=%s", slot, resp.status_code)
    except Exception as exc:  # noqa: BLE001 — 트리거 실패가 스케줄러를 멈추면 안 된다
        logger.error("[scheduler] collect 트리거 실패 — slot=%s error=%s", slot, exc)


def _run_batches(slot: str) -> None:
    """큐레이션 → 보관 순서로 실행한다. 동기 함수라 APScheduler가 스레드에서 돌린다.

    `app.batch.*.run`을 부르는 이유: 그 안에서 batch_jobs/job_logs에 실행 이력과 오류를
    남긴다(§9). 서비스 함수를 직접 부르면 관리자 파이프라인 화면에 아무것도 안 남는다.
    """
    client = redis.Redis(connection_pool=_pool)
    try:
        if not _acquire_lock(client, "FEED", slot):
            logger.info("[scheduler] 이미 실행됨, 건너뜀 — slot=%s", slot)
            return
    finally:
        client.close()

    db = SessionLocal()
    try:
        # task_ref는 batch_jobs에서 UNIQUE다. 락이 뚫려도 여기서 두 번째 실행이 막힌다.
        result = curate.run(db, task_ref=f"curate:{slot}:{date.today().isoformat()}")
        logger.info(
            "[scheduler] 큐레이션 완료 — slot=%s 생성=%d 요약없음=%d 중복=%d",
            slot, result.created_items, result.skipped_no_summary, result.skipped_duplicate,
        )
        ret = retention.run(db, task_ref=f"retention:{slot}:{date.today().isoformat()}")
        logger.info(
            "[scheduler] 보관 완료 — slot=%s 피드=%d 요약=%d 원문=%d",
            slot, ret.deleted_feed_items, ret.deleted_summaries, ret.deleted_articles,
        )
    except Exception as exc:  # noqa: BLE001 — 한 슬롯 실패가 다음 슬롯을 막지 않는다
        logger.error("[scheduler] 배치 실패 — slot=%s error=%s", slot, exc)
    finally:
        db.close()


def build_scheduler() -> AsyncIOScheduler:
    """`main.py`의 lifespan에서 호출한다. 슬롯은 설정(batch_slots)에서 읽는다."""
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    for slot in settings.batch_slots:
        hour, minute = _slot_to_time(slot)
        scheduler.add_job(
            trigger_collect,
            trigger="cron",
            hour=hour,
            minute=minute,
            kwargs={"slot": slot},
            id=f"collect_{slot}",
            replace_existing=True,
        )
        # A+B가 끝나기를 기다렸다가 C 배치를 돌린다.
        curate_minute = (minute + settings.curate_offset_minutes) % 60
        curate_hour = (hour + (minute + settings.curate_offset_minutes) // 60) % 24
        scheduler.add_job(
            _run_batches,
            trigger="cron",
            hour=curate_hour,
            minute=curate_minute,
            kwargs={"slot": slot},
            id=f"curate_{slot}",
            replace_existing=True,
        )

    return scheduler
