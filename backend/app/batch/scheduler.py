"""배치 스케줄러 (C 소유).

07:00 / 12:00 / 17:00 에 A+B 수집·요약 파이프라인을 트리거하고,
CURATE_OFFSET_MIN 후에 C의 큐레이션·보관 배치를 실행한다.

실행기 결합 규칙(CLAUDE.md §2):
  - 스케줄 시각 상수는 이 파일에만 선언한다.
  - curate / retention 로직은 해당 모듈의 run() 함수를 호출할 뿐,
    이 파일에 비즈니스 로직을 직접 작성하지 않는다.

[PROVISIONAL] A_COLLECT_ENDPOINT 는 A 담당자에게 실제 경로를 받으면
이 파일의 상수만 수정한다. 라우터·서비스 코드는 바꾸지 않는다.
"""

import logging

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# ── 설정 상수 ─────────────────────────────────────────────────────────────────

# [PROVISIONAL] A 담당자에게 실제 경로/인증 방식 수령 후 수정
A_COLLECT_ENDPOINT = "http://localhost:8000/internal/batch/collect"

# 배치 슬롯 (CLAUDE.md §1: 하루 3회 07/12/17)
PIPELINE_SLOTS = [
    {"hour": 7,  "minute": 0},
    {"hour": 12, "minute": 0},
    {"hour": 17, "minute": 0},
]

# A+B 파이프라인 완료 대기 오프셋 (분)
# A 엔드포인트가 동기(완료 후 응답)로 확정되면 trigger_curate를 trigger_collect
# 콜백으로 이동하고 이 오프셋은 제거한다.
CURATE_OFFSET_MIN = 30

# [PROVISIONAL] DB URL — app.core.config 가 공용 스켈레톤에 생기면 그쪽에서 가져온다.
DATABASE_URL = "mysql+pymysql://user:password@localhost:3306/news_ai"


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _get_db_session():
    """공용 get_db 의존성이 없는 동안 스케줄러 전용으로 직접 세션을 만든다.
    app.db.session.get_db 가 생기면 이 함수를 제거하고 그쪽으로 교체한다."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()


# ── 작업 함수 ─────────────────────────────────────────────────────────────────

async def trigger_collect(slot: str) -> None:
    """A+B 파이프라인 HTTP 트리거."""
    logger.info("[scheduler] collect trigger start — slot=%s", slot)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                A_COLLECT_ENDPOINT,
                json={"slot": slot},
            )
            resp.raise_for_status()
        logger.info("[scheduler] collect trigger success — slot=%s status=%s", slot, resp.status_code)
    except Exception as exc:
        logger.error("[scheduler] collect trigger failed — slot=%s error=%s", slot, exc)


async def trigger_curate(slot: str) -> None:
    """C 큐레이션·보관 배치 실행."""
    from app.modules.feed.services.curation_service import run_curation
    from app.modules.feed.services.retention_service import run_retention

    logger.info("[scheduler] curate start — slot=%s", slot)
    db = _get_db_session()
    try:
        result = run_curation(db)
        logger.info(
            "[scheduler] curate done — slot=%s created=%d skipped_no_summary=%d skipped_dup=%d",
            slot, result.created_items, result.skipped_no_summary, result.skipped_duplicate,
        )
        ret = run_retention(db)
        logger.info("[scheduler] retention done — slot=%s deleted=%d", slot, ret.deleted_items)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("[scheduler] curate failed — slot=%s error=%s", slot, exc)
    finally:
        db.close()


# ── 스케줄러 빌더 ─────────────────────────────────────────────────────────────

def build_scheduler() -> AsyncIOScheduler:
    """main.py lifespan 에서 호출한다."""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    slot_labels = {7: "0700", 12: "1200", 17: "1700"}

    for slot in PIPELINE_SLOTS:
        h = slot["hour"]
        label = slot_labels[h]

        scheduler.add_job(
            trigger_collect,
            trigger="cron",
            hour=h,
            minute=0,
            kwargs={"slot": label},
            id=f"collect_{label}",
            replace_existing=True,
        )
        scheduler.add_job(
            trigger_curate,
            trigger="cron",
            hour=h,
            minute=CURATE_OFFSET_MIN,
            kwargs={"slot": label},
            id=f"curate_{label}",
            replace_existing=True,
        )

    return scheduler
