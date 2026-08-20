"""비밀번호 해시 유틸. 평문/복호화 가능 암호화 금지 (SKILL §6)."""

from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    return _ctx.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _ctx.verify(raw, hashed)
