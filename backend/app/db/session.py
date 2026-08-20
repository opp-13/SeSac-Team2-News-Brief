"""DB 세션 (공용 영역).

동기 SQLAlchemy 세션을 쓴다. 각 모듈의 서비스가 `db.commit()`을 await 없이 호출하고
있어(`modules/feed/services/*`, `modules/auth/services/*`) 비동기 세션으로 바꾸면
전 모듈이 깨진다. 바꾸려면 공용 PR + 전원 리뷰가 필요하다.

커밋은 서비스/배치 계층이 직접 한다. 여기서 자동 커밋하지 않는다 — 배치가
`db.rollback()` 후 오류를 기록하는 흐름(`batch/curate.py`)이 성립해야 하기 때문이다.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,  # 유휴 커넥션이 MySQL wait_timeout으로 끊긴 경우를 걸러낸다
    echo=_settings.debug,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성. 요청 단위로 세션을 열고 반드시 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
