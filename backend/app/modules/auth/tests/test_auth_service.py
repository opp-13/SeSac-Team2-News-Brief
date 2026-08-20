"""정상 경로 1개 + 실패 경로 1개 (SKILL §8)."""

import pytest

from app.common.exceptions import ConflictError, UnauthorizedError
from app.modules.auth.services import auth_service, session_service


def _signup(db):
    return auth_service.signup(
        db, email="c@example.com", password="password123", nickname="C", preferred_language="ko"
    )


def test_signup_and_login_creates_session(db, redis):
    """정상: 가입 후 로그인하면 Redis 세션이 생성되고 조회된다."""
    _signup(db)

    user, session_id = auth_service.login(
        db, redis, email="c@example.com", password="password123"
    )

    assert user.email == "c@example.com"
    session = session_service.get_session(redis, session_id)
    assert session is not None and session.user_id == user.id

    auth_service.logout(redis, session_id)
    assert session_service.get_session(redis, session_id) is None


def test_login_with_wrong_password_raises(db, redis):
    """실패: 비밀번호가 틀리면 세션을 만들지 않고 401 계열 예외를 던진다."""
    _signup(db)

    with pytest.raises(UnauthorizedError):
        auth_service.login(db, redis, email="c@example.com", password="wrong-password")


def test_duplicate_email_raises(db):
    """실패: 동일 이메일 재가입은 거부한다."""
    _signup(db)
    with pytest.raises(ConflictError):
        _signup(db)
