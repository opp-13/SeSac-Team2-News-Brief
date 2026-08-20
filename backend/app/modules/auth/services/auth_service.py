"""회원가입/로그인 비즈니스 로직. 라우터에는 로직을 두지 않는다 (SKILL §4-4)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import ConflictError, UnauthorizedError  # 공용 — 수정하지 않음
from app.modules.auth.models.user import User
from app.modules.auth.services import session_service
from app.modules.auth.services.password import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def signup(db: Session, *, email: str, password: str, nickname: str, preferred_language: str) -> User:
    if get_user_by_email(db, email) is not None:
        raise ConflictError("EMAIL_ALREADY_EXISTS")

    user = User(
        email=email,
        password_hash=hash_password(password),
        nickname=nickname,
        preferred_language=preferred_language,
    )
    db.add(user)
    db.flush()
    return user


def login(db: Session, redis, *, email: str, password: str) -> tuple[User, str]:
    user = get_user_by_email(db, email)
    # 존재하지 않는 이메일과 비밀번호 불일치를 구분해 노출하지 않는다.
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("INVALID_CREDENTIALS")
    if user.status != "ACTIVE":
        raise UnauthorizedError("INACTIVE_USER")

    session_id = session_service.create_session(
        redis,
        session_service.SessionData(user_id=user.id, preferred_language=user.preferred_language),
    )
    return user, session_id


def logout(redis, session_id: str) -> None:
    session_service.delete_session(redis, session_id)


def change_password(db: Session, *, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError("INVALID_CREDENTIALS")
    user.password_hash = hash_password(new_password)
    db.flush()
