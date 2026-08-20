"""FastAPI 애플리케이션 진입점.

[공용 파일 — 변경 시 전원 리뷰 PR 필요 (CLAUDE.md §5)]

라우터 등록 순서:
  auth_router   — C 담당
  feed_router   — C 담당
  tag_router    — C 담당
  my_tag_router — C 담당

다른 모듈(A·B) 라우터는 각 담당자가 별도 PR로 추가한다.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.batch.scheduler import build_scheduler
from app.modules.auth.routers.auth_router import router as auth_router
from app.modules.feed.routers.feed_router import router as feed_router
from app.modules.feed.routers.tag_router import my_tag_router, tag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = build_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="NewsBrief API",
    lifespan=lifespan,
)

# ── 라우터 등록 ────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(tag_router)
app.include_router(my_tag_router)
