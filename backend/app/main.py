"""FastAPI 애플리케이션 엔트리포인트 (공용 영역).

여러 모듈이 함께 쓰는 파일이다. 고쳤으면 팀에 알린다 (CLAUDE.md §5 충돌 방지 규칙 1).
라우터 등록 외의 비즈니스 로직을 여기에 쓰지 않는다.

실행:
    cd backend
    uvicorn app.main:app --reload    # http://localhost:8000/docs

응답 형태는 모두 봉투로 감싸진다 — `{success, data}` / `{success, error}`.
자세한 이유와 한계는 `app/common/response.py` 참고.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.meta_router import router as meta_router
from app.common.response import EnvelopeMiddleware, register_exception_handlers
from app.core.config import get_settings
from app.modules.auth.routers.auth_router import router as auth_router
from app.modules.feed.routers.feed_router import router as feed_router
from app.modules.feed.routers.tag_router import my_tag_router, tag_router

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    debug=settings.debug,
)

# CORS는 프런트를 다른 오리진(예: Vite 5173)에서 띄울 때만 필요하다. nginx로 같은
# 도메인에서 서빙하면 cors_origins를 비워 둔다.
# allow_credentials=True 이므로 와일드카드 오리진은 쓸 수 없다 —
# 세션 쿠키(credentials: 'include')가 전달되어야 하기 때문이다.
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 미들웨어는 나중에 추가한 것이 바깥쪽에서 먼저 돈다. 봉투 래핑은 CORS 헤더가 붙은
# 뒤에 본문만 손대야 하므로 CORS보다 뒤에 등록한다.
app.add_middleware(EnvelopeMiddleware)

register_exception_handlers(app)

# --- 라우터 등록 -------------------------------------------------------------
# 각 라우터가 자기 prefix를 들고 있다 (modules/*/api_paths.py). 여기서 prefix를
# 덧붙이지 않는다 — 두 곳에서 경로를 정하면 정합 시 어디를 고쳐야 할지 알 수 없다.
API_PREFIX = "/api/v1"

app.include_router(meta_router, prefix=API_PREFIX)
app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(tag_router)
app.include_router(my_tag_router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    """로드밸런서·컨테이너 헬스체크용. 봉투를 씌우지 않는다
    (`response.EXCLUDED_PATHS`) — 헬스체크 도구가 표준 형태를 기대한다."""
    return {"status": "ok"}
