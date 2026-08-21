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

    # --- 배치 ---
    batch_slots: list[str] = Field(default_factory=lambda: ["0700", "1200", "1700"])

    scheduler_enabled: bool = False
    """스케줄러 기동 여부. **기본은 꺼짐이다.**

    켜져 있으면 앱을 띄우는 것만으로 보관 배치가 돌고, 보관 배치는 되돌릴 수 없는
    삭제를 한다(hard delete). 개발 중에 uvicorn을 띄웠다가 데이터가 사라지는 일이
    없도록 명시적으로 켜야만 동작하게 한다. `--reload`는 프로세스를 둘 띄우므로
    그 상태로 켜면 중복 실행이 되기도 한다(락으로 막지만 굳이 그럴 이유가 없다)."""

    curate_offset_minutes: int = 30
    """수집·요약(A+B) 파이프라인이 끝나기를 기다리는 오프셋.

    A의 트리거가 동기(완료 후 응답)로 확정되면 이 오프셋을 없애고 콜백으로 바꾼다."""

    collect_trigger_url: str | None = None
    """A+B 파이프라인을 깨우는 HTTP 엔드포인트. 미정이라 기본은 None이고,
    비어 있으면 수집 트리거 단계를 건너뛴다 — 없는 주소로 매 슬롯 실패 로그를 쌓지 않는다.

    `collect_root`가 설정돼 있으면 이쪽 대신 CLI 서브프로세스로 수집한다
    (`app/batch/collect.py`). 둘 다 비어 있으면 수집 단계를 건너뛴다."""

    # --- 수집 (app/batch/collect.py) ---
    collect_root: str | None = None
    """newscollect 패키지 경로. 비어 있으면 수집 배치를 건너뛴다 (기본 동작).

    수집기는 CLI만 제공하고 HTTP 서버가 없어서 서브프로세스로 부른다. 경로를 코드에
    박지 않는 이유는 배포 형태가 정해지지 않았기 때문이다 — 같은 머신에 두 디렉토리가
    나란히 있는 지금 구조에 의존하는 값이라 설정으로 뺀다."""

    collect_python: str | None = None
    """수집기를 돌릴 파이썬 실행 파일. 비어 있으면 `{collect_root}/.venv/bin/python`.

    백엔드 venv와 다르다 — 수집기는 sentence-transformers/torch를 쓰고 백엔드는 쓰지 않는다."""

    collect_provider: str = "freenews"
    """수집 대상 프로바이더. 현재 freenews 단독이다.

    naver는 (1) 카테고리 개념이 없어 63개 topic을 자유 검색어로 던져야 하고,
    (2) description이 130~190자뿐이라 요약 입력으로 부족하며(출력이 입력보다 길어진다),
    (3) 일별 호출 한도가 Groq 예산보다 먼저 걸린다. freenews는 63개 topic이 그대로
    `tags.slug`와 일치한다 (CLAUDE.md §8-16)."""

    collect_display: int = 2
    """카테고리당 수집 건수. 예산 근거는 app/batch/collect.py 상단 주석 참고."""

    collect_language: str = "en"
    """freenews 검색 언어. 영문 기사를 받아 한국어로 번역하는 것이 이 서비스의 핵심이다."""

    collect_timeout_seconds: int = 300
    """카테고리 1건의 타임아웃. 실측 약 20초(display=2)라 넉넉하게 잡았다."""

    groq_daily_token_budget: int = 200_000
    """Groq 하루 토큰 한도. 초과하면 남은 카테고리를 건너뛴다."""

    groq_tokens_per_article: int = 1_200
    """기사 1건 요약의 토큰 추정치.

    실측값: freenews 본문 요약이 802~1,003 토큰(max_tokens=300 기준). 절단을 고치려고
    max_tokens를 올리면 completion이 늘어나므로 여유를 얹어 1,200으로 잡았다.
    **추정치인 이유**: 수집기가 Groq `usage` 응답을 버려서 실제 사용량을 알 수 없다.
    B가 usage를 반환하게 고치면 이 상수 대신 실측 누적으로 바꾼다."""


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
