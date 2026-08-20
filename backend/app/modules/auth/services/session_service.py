"""Redis 세션 서비스.

Redis는 세션/캐시/락 전용이며 기사·요약 본문을 여기에 저장하지 않는다 (CLAUDE.md §8-6).
"""

import json
import secrets
from dataclasses import dataclass

SESSION_KEY_PREFIX = "session:"          # [PROV-A20] 키 설계는 schema.sql 하단 주석 기준으로 검증 필요
DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # [OPEN] 설정으로 외부화 대상


@dataclass(frozen=True)
class SessionData:
    user_id: int
    preferred_language: str


def _key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def create_session(redis, data: SessionData, ttl: int = DEFAULT_SESSION_TTL_SECONDS) -> str:
    session_id = secrets.token_urlsafe(32)
    redis.setex(
        _key(session_id),
        ttl,
        json.dumps({"user_id": data.user_id, "preferred_language": data.preferred_language}),
    )
    return session_id


def get_session(redis, session_id: str) -> SessionData | None:
    raw = redis.get(_key(session_id))
    if raw is None:
        return None
    payload = json.loads(raw if isinstance(raw, str) else raw.decode())
    return SessionData(
        user_id=int(payload["user_id"]),
        preferred_language=payload.get("preferred_language", "ko"),
    )


def delete_session(redis, session_id: str) -> None:
    redis.delete(_key(session_id))
