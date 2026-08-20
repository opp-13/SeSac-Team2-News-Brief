"""auth 라우터. 경로 문자열은 반드시 `api_paths`에서 가져온다 (계약 확정 시 일괄 변경용)."""

from fastapi import APIRouter, Depends, Response, status

from app.core.redis import get_redis
from app.db.session import get_db
from app.modules.auth import api_paths
from app.modules.auth.dependencies import get_current_user, get_session_id
from app.modules.auth.models.user import User
from app.modules.auth.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    SignupRequest,
    UserResponse,
)
from app.modules.auth.services import auth_service

router = APIRouter(prefix=api_paths.AUTH_PREFIX, tags=["auth"])


@router.post(api_paths.SIGNUP, response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db=Depends(get_db)) -> User:
    user = auth_service.signup(
        db,
        email=body.email,
        password=body.password,
        nickname=body.nickname,
        preferred_language=body.preferred_language,
    )
    db.commit()
    return user


@router.post(api_paths.LOGIN, response_model=LoginResponse)
def login(body: LoginRequest, response: Response, db=Depends(get_db), redis=Depends(get_redis)):
    user, session_id = auth_service.login(db, redis, email=body.email, password=body.password)
    db.commit()
    response.set_cookie(
        api_paths.SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        samesite="lax",  # [PROV-A06] 배포 도메인 구성 확정 후 조정
    )
    return LoginResponse(user=UserResponse.model_validate(user), session_id=session_id)


@router.post(api_paths.LOGOUT, status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, session_id: str = Depends(get_session_id), redis=Depends(get_redis)):
    auth_service.logout(redis, session_id)
    response.delete_cookie(api_paths.SESSION_COOKIE_NAME)


@router.get(api_paths.ME, response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch(api_paths.ME_PASSWORD, status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    auth_service.change_password(
        db, user=user, current_password=body.current_password, new_password=body.new_password
    )
    db.commit()
