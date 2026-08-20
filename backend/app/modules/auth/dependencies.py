"""세션 기반 인증 의존성.

[PROVISIONAL] 세션 전달 방식(쿠키 vs Authorization 헤더)은 D의 계약 확정 대상이다.
현재는 쿠키 우선 + 헤더 fallback으로 두되, 확정되면 한쪽만 남긴다. [PROV-A06]
"""

from fastapi import Depends, Request

from app.common.exceptions import ForbiddenError, UnauthorizedError
from app.core.redis import get_redis  # 공용 — 수정하지 않음
from app.db.session import get_db  # 공용 — 수정하지 않음
from app.modules.auth import api_paths
from app.modules.auth.models.user import User
from app.modules.auth.services import auth_service, session_service


def get_session_id(request: Request) -> str:
    session_id = request.cookies.get(api_paths.SESSION_COOKIE_NAME)
    if not session_id:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            session_id = header.removeprefix("Bearer ").strip()
    if not session_id:
        raise UnauthorizedError("NO_SESSION")
    return session_id


def get_current_user(
    session_id: str = Depends(get_session_id),
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    session = session_service.get_session(redis, session_id)
    if session is None:
        raise UnauthorizedError("SESSION_EXPIRED")
    user = auth_service.get_user_by_id(db, session.user_id)
    if user is None:
        raise UnauthorizedError("SESSION_EXPIRED")
    return user


def get_current_user_optional(
    request: Request,
    db=Depends(get_db),
    redis=Depends(get_redis),
) -> User | None:
    """로그인했으면 User, 아니면 None. **401을 던지지 않는다.**

    피드 목록은 같은 엔드포인트가 로그인 여부로 두 가지로 동작한다
    (`docs/api-contracts/feed.md` — 게스트는 articles 최신순, 로그인은 feed_items).
    게스트에게 401을 주면 서비스 첫 화면이 열리지 않으므로 이 의존성을 쓴다.

    세션 쿠키가 있지만 만료된 경우도 게스트로 취급한다 — 첫 화면에서 로그인을
    강제하지 않는 것이 목적이고, 보호가 필요한 엔드포인트는 get_current_user를 쓴다.
    """
    session_id = request.cookies.get(api_paths.SESSION_COOKIE_NAME)
    if not session_id:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            session_id = header.removeprefix("Bearer ").strip()
    if not session_id:
        return None

    session = session_service.get_session(redis, session_id)
    if session is None:
        return None
    return auth_service.get_user_by_id(db, session.user_id)


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """관리자 전용 엔드포인트 가드.

    로그인 여부는 `get_current_user`가 이미 확인한다. 여기서는 권한만 본다 —
    401(로그인 안 함)과 403(로그인했지만 권한 없음)을 구분해야 프런트가
    "로그인 화면으로 보낼지 / 권한 없음을 보여줄지"를 정할 수 있다.
    """
    if user.role != "ADMIN":
        raise ForbiddenError("ADMIN_REQUIRED")
    return user
