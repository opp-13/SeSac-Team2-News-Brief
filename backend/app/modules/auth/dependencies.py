"""세션 기반 인증 의존성.

[PROVISIONAL] 세션 전달 방식(쿠키 vs Authorization 헤더)은 D의 계약 확정 대상이다.
현재는 쿠키 우선 + 헤더 fallback으로 두되, 확정되면 한쪽만 남긴다. [PROV-A06]
"""

from fastapi import Depends, Request

from app.common.exceptions import UnauthorizedError
from app.core.redis import get_redis  # 공용 — 수정하지 않음
from app.db.session import get_db     # 공용 — 수정하지 않음
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
