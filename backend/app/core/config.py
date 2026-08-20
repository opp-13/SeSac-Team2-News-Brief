"""애플리케이션 설정 (공용 영역).

시크릿은 코드에 넣지 않는다 (CLAUDE.md §7). 모든 값은 환경변수 또는 `backend/.env`에서
읽고, 커밋되는 것은 `backend/.env.example`의 플레이스홀더뿐이다.

배치 실행 시각(07:00/12:00/17:00)은 스케줄러 기술이 미정이라(§8 미결 사항) 여기에
설정값으로만 두고, 특정 스케줄러 라이브러리를 끌어오지 않는다.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 필수 (기본값을 주지 않는다 — 누락 시 기동 시점에 바로 실패시킨다) ---
    database_url: str = Field(
        description="예: mysql+pymysql://user:pass@localhost:3306/news_ai?charset=utf8mb4",
    )
    redis_url: str = Field(description="예: redis://localhost:6379/0")

    # --- 앱 ---
    app_name: str = "NewsBrief API"
    api_version: str = "dev"
    """`GET /meta/deploy-info`가 프런트 헤더에 노출하는 값. CI 빌드/배포 시 주입한다."""
    debug: bool = False

    # --- CORS ---
    # 프런트를 같은 도메인에서 nginx로 서빙하면 비워 둔다(동일 출처라 CORS 불필요).
    # Vite 개발 서버(5173)에서 직접 호출할 때만 필요하다.
    cors_origins: list[str] = Field(default_factory=list)

    # --- 세션 ---
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    session_cookie_secure: bool = True
    """로컬 http 개발에서는 False로 내려야 브라우저가 쿠키를 저장한다."""

    # --- 배치 (실행기 비의존 — 트리거는 기술 확정 후 별도 계층) ---
    batch_slots: list[str] = Field(default_factory=lambda: ["0700", "1200", "1700"])


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
