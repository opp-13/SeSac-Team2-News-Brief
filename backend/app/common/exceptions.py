"""공통 예외 (공용 영역).

각 모듈은 **코드 문자열**만 넘긴다 — 기존 호출 형태를 그대로 유지했다:

    raise NotFoundError("FEED_ITEM_NOT_FOUND")
    raise ConflictError("EMAIL_ALREADY_EXISTS")
    raise UnauthorizedError("NO_SESSION")
    raise NotFoundError(f"TAG_NOT_FOUND: {missing}")   # 코드 뒤에 상세를 붙이는 형태도 허용

사용자에게 보일 한국어 문구는 여기 한 곳에서 코드→메시지로 매핑한다. 서비스 계층이
문구를 들고 있으면 같은 오류의 문구가 모듈마다 갈라진다.

HTTP 상태코드와 `{code, message}` 직렬화는 `app/common/response.py`의 예외 핸들러가
담당한다. 서비스는 상태코드를 몰라도 된다.
"""

# 코드 → 사용자 노출 문구. 없으면 클래스의 기본 문구를 쓴다.
# 프런트는 code로 분기하고 message는 그대로 표시한다 (docs/api-contracts/*.md).
MESSAGES: dict[str, str] = {
    # auth
    "NO_SESSION": "로그인이 필요합니다.",
    "SESSION_EXPIRED": "세션이 만료되었습니다. 다시 로그인해주세요.",
    "INVALID_CREDENTIALS": "이메일 또는 비밀번호가 올바르지 않습니다.",
    "INACTIVE_USER": "사용할 수 없는 계정입니다.",
    "EMAIL_ALREADY_EXISTS": "이미 사용 중인 이메일입니다.",
    # feed / tag
    "FEED_ITEM_NOT_FOUND": "요청한 피드 항목을 찾을 수 없습니다.",
    "ARTICLE_NOT_FOUND": "요청한 기사를 찾을 수 없습니다.",
    "BOOKMARK_NOT_FOUND": "북마크를 찾을 수 없습니다.",
    "TAG_NOT_FOUND": "존재하지 않는 태그입니다.",
    "USER_TAG_NOT_FOUND": "등록되지 않은 관심 태그입니다.",
}


class AppError(Exception):
    """애플리케이션이 의도적으로 발생시키는 오류의 베이스."""

    status_code: int = 500
    default_message: str = "요청을 처리할 수 없습니다."

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        self.message = message or self._lookup_message(code)
        super().__init__(f"{code}: {self.message}")

    @classmethod
    def _lookup_message(cls, code: str) -> str:
        # "TAG_NOT_FOUND: [3]" 처럼 코드 뒤에 상세가 붙은 경우도 앞부분으로 찾는다.
        return MESSAGES.get(code) or MESSAGES.get(code.split(":", 1)[0].strip()) or cls.default_message


class BadRequestError(AppError):
    status_code = 400
    default_message = "요청 형식이 올바르지 않습니다."


class UnauthorizedError(AppError):
    status_code = 401
    default_message = "로그인이 필요합니다."


class ForbiddenError(AppError):
    status_code = 403
    default_message = "권한이 없습니다."


class NotFoundError(AppError):
    status_code = 404
    default_message = "요청한 리소스를 찾을 수 없습니다."


class ConflictError(AppError):
    status_code = 409
    default_message = "이미 존재하는 리소스입니다."
