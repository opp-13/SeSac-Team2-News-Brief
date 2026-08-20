"""Redis 클라이언트 (공용 영역).

용도는 **세션 / 캐시 / 락뿐이다.** 요약·번역 본문을 Redis에만 두는 구현은 금지
(CLAUDE.md §8-6, 영구 저장은 MySQL). 배치 브로커 용도도 실행 기술이 확정되기 전까지
쓰지 않는다 (§8-2).

동기 클라이언트를 쓴다 — `modules/auth/services/session_service.py`가
`redis.setex()` / `redis.get()`을 await 없이 호출하고 있어서, 비동기 클라이언트로
바꾸면 auth 모듈이 깨진다.

`decode_responses=True`로 두어 `get()`이 str을 돌려준다. session_service는 bytes도
처리하도록 방어적으로 쓰여 있어 두 경우 모두 동작한다.
"""

from collections.abc import Generator

import redis

from app.core.config import get_settings

_settings = get_settings()

# 커넥션 풀은 프로세스당 하나만 만든다. 요청마다 새 풀을 만들면 커넥션이 누적된다.
_pool = redis.ConnectionPool.from_url(_settings.redis_url, decode_responses=True)


def get_redis() -> Generator[redis.Redis, None, None]:
    """FastAPI 의존성. 풀에서 커넥션을 빌려 쓰고 반납한다."""
    client = redis.Redis(connection_pool=_pool)
    try:
        yield client
    finally:
        client.close()
