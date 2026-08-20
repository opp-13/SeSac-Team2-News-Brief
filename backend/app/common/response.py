"""응답 래핑 + 예외 핸들러 (공용 영역).

프런트 계약(`docs/api-contracts/*.md`, `frontend/src/api/client.ts`)이 정한 형태:

    성공  { "success": true,  "data": <응답 본문> }
    실패  { "success": false, "error": { "code": "...", "message": "..." } }

**왜 미들웨어로 감싸는가** — 래핑을 각 라우터의 `response_model`로 표현하려면 모든
모듈의 라우터를 고쳐야 하고, 새 엔드포인트를 만들 때마다 빠뜨릴 수 있다. 여기서 한 번에
감싸면 모듈은 평소처럼 Pydantic 모델을 반환하면 된다.

**대가**: `/docs`의 OpenAPI 스키마에는 래핑이 반영되지 않는다(모듈이 선언한 원래 모델이
그대로 보인다). 실제 응답과 문서가 한 겹 다르다는 점을 팀에 공지해야 한다.

**204는 200으로 바꿔 내려보낸다.** 봉투 형식은 본문을 전제하는데 204는 본문을 가질 수
없다. 프런트 `apiFetch`도 모든 응답에서 `res.json()`을 호출하므로 204가 오면 파싱이
깨진다. 그래서 로그아웃·태그 삭제처럼 `status_code=204`로 선언된 라우터도 여기서
`200 { success: true, data: null }`로 정규화한다 — C의 라우터를 고치지 않아도 된다.
"""

import json
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.common.exceptions import AppError

logger = logging.getLogger(__name__)

# 봉투를 씌우지 않는 경로 — 문서/스펙/헬스체크는 표준 형식이어야 도구가 읽는다.
EXCLUDED_PATHS = frozenset({"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect", "/health"})

# HTTP 상태코드 → 기본 에러 코드. 프레임워크가 직접 낸 오류에 쓴다.
_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
}


def success(data: object) -> dict:
    return {"success": True, "data": data}


def failure(code: str, message: str) -> dict:
    return {"success": False, "error": {"code": code, "message": message}}


class EnvelopeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001, ANN201
        response = await call_next(request)

        if request.url.path in EXCLUDED_PATHS:
            return response

        # 4xx·5xx는 아래 예외 핸들러들이 이미 봉투를 씌워 내려보낸다.
        if response.status_code >= 400:
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])

        # 본문 없는 성공 응답(204 등)은 data: null 로 정규화한다.
        if not body:
            return _wrap(response, success(None))

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            # 파일 다운로드·리다이렉트 등은 손대지 않고 그대로 통과시킨다.
            return _passthrough(response, body)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("JSON 응답을 파싱하지 못해 래핑을 건너뜁니다: %s", request.url.path)
            return _passthrough(response, body)

        return _wrap(response, success(payload))


def _carry_over_headers(source, target: Response) -> None:  # noqa: ANN001
    """원본 응답의 헤더를 새 응답으로 옮긴다.

    **왜 필요한가**: 라우터가 `response.set_cookie()`로 붙인 `Set-Cookie`가 여기서
    유실되면 로그인이 되지 않는다(응답은 200인데 세션 쿠키가 없어 다음 요청이 401).
    실제로 이 누락 때문에 로그인 → /auth/me 흐름이 깨졌다.

    `dict(headers)`를 쓰지 않는 이유: 같은 이름의 헤더가 여러 개일 수 있고(Set-Cookie가
    대표적) dict로 만들면 하나만 남는다. 그래서 raw_headers를 그대로 옮긴다.

    content-length / content-type은 옮기지 않는다 — 본문을 새로 만들었으므로
    새 응답이 계산한 값이 맞다.
    """
    skip = {b"content-length", b"content-type"}
    for key, value in source.raw_headers:
        if key.lower() not in skip:
            target.raw_headers.append((key, value))


def _wrap(source, payload: dict) -> Response:  # noqa: ANN001
    """봉투를 씌운 새 응답을 만들되 원본 헤더(쿠키 등)를 잃지 않는다."""
    wrapped = JSONResponse(payload, status_code=200)
    _carry_over_headers(source, wrapped)
    return wrapped


def _passthrough(response, body: bytes) -> Response:  # noqa: ANN001
    """본문을 이미 읽어버린(body_iterator를 소비한) 응답을 그대로 다시 만들어 준다."""
    out = Response(
        content=body,
        status_code=response.status_code,
        media_type=response.headers.get("content-type"),
    )
    _carry_over_headers(response, out)
    return out


def register_exception_handlers(app: FastAPI) -> None:
    """모든 오류 응답이 같은 봉투 형태를 갖도록 핸들러를 등록한다."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
        return JSONResponse(failure(exc.code, exc.message), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:  # noqa: ARG001
        # 어느 필드가 문제인지까지 알려준다 — 프런트 폼 오류 표시에 필요하다.
        fields = ", ".join(".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()) or "요청 본문"
        return JSONResponse(
            failure("VALIDATION_ERROR", f"입력값이 올바르지 않습니다: {fields}"),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:  # noqa: ARG001
        code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else code
        return JSONResponse(failure(code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # 내부 예외 내용을 클라이언트에 노출하지 않는다. 추적은 서버 로그로 한다.
        logger.exception("처리되지 않은 예외: %s %s", request.method, request.url.path)
        return JSONResponse(
            failure("INTERNAL_ERROR", "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."),
            status_code=500,
        )
