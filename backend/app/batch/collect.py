"""수집 배치.

**소유권 안내 (CLAUDE.md §5 규칙 4)**: `batch/collect.py`는 A 소유 파일이다. 스케줄러에
붙일 수집 로직이 없어 C가 초안을 작성했으니, A가 이어받아 관리한다.

---
**왜 서브프로세스인가.** `newscollect`는 CLI만 제공하고 HTTP 서버가 없다. §8-19의
`COLLECT_TRIGGER_URL`은 A가 엔드포인트를 만들 때를 위한 자리였는데 아직 없다. 그렇다고
백엔드가 `newscollect`를 import 하면 (1) §5 규칙 2(다른 모듈 폴더 직접 import 금지)를
어기고, (2) torch/sentence-transformers가 백엔드 프로세스에 딸려 들어온다. CLI를 그대로
부르는 쪽이 경계를 지킨다.

**실행기 비의존 (§2)**: 이 파일에는 스케줄러 데코레이터도 브로커 설정도 없다. `run()`은
인자를 받아 결과를 반환할 뿐이고, 트리거는 `batch/scheduler.py`가 담당한다.

---
**수집 전략 (실측 기반)**

63개 카테고리를 슬롯 수로 나눠 하루에 정확히 한 번씩 전부 돈다.

    63 카테고리 ÷ 3 슬롯 = 슬롯당 21개
    21 × display 2 = 슬롯당 42건, 하루 126건

Groq 예산(하루 200k 토큰):

    freenews 본문 요약 실측  802~1,003 토큰/건 (max_tokens=300 기준)
    max_tokens 절단 수정 후  약 1,200 토큰/건으로 추정
    126건 × 1,200 = 151,200 토큰 = 한도의 76%

나머지 24%는 재시도와 추정 오차를 위한 여유다. `display=3`으로 올리면 189건 × 1,200 =
226,800으로 **한도를 넘는다** — 지금 예산에서 깊이를 늘릴 여지는 없다.

**freenews는 `--with-body`가 필수다.** URL을 상세 조회 단계에서 채우기 때문에, 이 플래그가
없으면 `articles.url`이 비어 수집기가 전부 저장을 건너뛴다(`[db] url 없음, 저장 skip`).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.batch_log import finish_job, log_error, start_job  # 공용 — 수정하지 않음
from app.core.config import get_settings
from app.modules.feed.models.read_only import Summary
from app.modules.feed.models.tag import TAG_TYPE_CATEGORY, Tag

JOB_NAME = "collect"


@dataclass
class CollectResult:
    slot: str
    attempted: list[str] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped_over_budget: list[str] = field(default_factory=list)
    articles_created: int = 0
    estimated_tokens: int = 0

    @property
    def status(self) -> str:
        if self.failed and not self.succeeded:
            return "FAILED"
        if self.failed or self.skipped_over_budget:
            return "PARTIAL"
        return "SUCCESS"


def category_slugs(db: Session) -> list[str]:
    """수집 대상 카테고리 슬러그 전체.

    `is_active`로 거르지 않는다 — 그 값은 **화면 노출 여부**일 뿐이고, 수집기는 비활성
    태그로도 태깅한다 (CLAUDE.md §8-16). 활성 12개만 모으면 게스트 피드가 그 12개
    주제로만 채워진다.
    """
    return list(
        db.scalars(
            select(Tag.slug).where(Tag.tag_type == TAG_TYPE_CATEGORY).order_by(Tag.slug)
        )
    )


def categories_for_slot(slugs: list[str], slot: str, slots: list[str]) -> list[str]:
    """이 슬롯이 맡을 카테고리.

    앞에서부터 잘라 나누지 않고 stride(`[i::n]`)로 흩는다. 슬러그는 알파벳순이라
    앞에서 자르면 이웃한 주제('mental health' / 'motor sports' / 'movies')가 한 슬롯에
    몰려 그 시간대 피드가 한쪽으로 쏠린다.

    슬롯 이름을 모르면 전체를 돌려준다 — 수동 실행(`slot='MANUAL'`)이 조용히 빈 목록을
    받아 아무것도 안 하는 것보다 낫다.
    """
    if slot not in slots or not slots:
        return list(slugs)
    return slugs[slots.index(slot) :: len(slots)]


def tokens_spent_today(db: Session) -> int:
    """오늘 이미 쓴 Groq 토큰 추정치.

    **추정인 이유**: 수집기가 Groq `usage` 응답을 버려 실제 사용량이 어디에도 남지 않는다.
    저장된 요약 건수 × 건당 추정치로 대신한다. 실패해서 버려진 호출은 세지 못하므로
    이 값은 항상 **과소 추정**이다 — 그래서 예산에 여유를 두고 쓴다.
    """
    settings = get_settings()
    today = datetime.now(timezone.utc).date()
    count = db.scalar(
        select(func.count()).select_from(Summary).where(func.date(Summary.created_at) == today)
    )
    return int(count or 0) * settings.groq_tokens_per_article


def _resolve_command(category: str) -> tuple[list[str], Path]:
    settings = get_settings()
    root = Path(settings.collect_root).expanduser().resolve()
    python = (
        Path(settings.collect_python).expanduser()
        if settings.collect_python
        else root / ".venv" / "bin" / "python"
    )
    cmd = [
        str(python),
        "main.py",
        "--category",
        category,  # 슬러그를 그대로 넘긴다 (main.py가 topic으로 정규화한다)
        "--provider",
        settings.collect_provider,
        "--display",
        str(settings.collect_display),
        "--language",
        settings.collect_language,
        # freenews는 이 플래그가 없으면 url이 비어 한 건도 저장되지 않는다 (상단 주석).
        "--with-body",
    ]
    return cmd, root


def _article_count(db: Session) -> int:
    from app.modules.feed.models.read_only import Article

    return int(db.scalar(select(func.count()).select_from(Article)) or 0)


def run(
    db: Session,
    *,
    slot: str = "MANUAL",
    categories: list[str] | None = None,
    task_ref: str | None = None,
) -> CollectResult:
    """배치 엔트리 함수. 실행 이력은 batch_jobs, 오류는 job_logs에 기록한다 (§9)."""
    settings = get_settings()
    result = CollectResult(slot=slot)

    if not settings.collect_root:
        # 설정이 비어 있으면 조용히 건너뛴다 — 경로를 추측해 남의 머신에서 엉뚱한 것을
        # 실행하지 않는다. 스케줄러도 같은 기준으로 로그만 남긴다.
        return result

    targets = (
        categories
        if categories is not None
        else categories_for_slot(category_slugs(db), slot, settings.batch_slots)
    )
    result.attempted = list(targets)

    job_id = start_job(
        db,
        job_name=JOB_NAME,
        task_ref=task_ref,
        slot=slot,
        target_count=len(targets),
        started_at=datetime.now(timezone.utc),
    )
    db.commit()  # 실행 이력을 먼저 확정한다 — 수집이 몇 분 걸려서 그 사이 조회가 가능해야 한다

    before = _article_count(db)
    spent = tokens_spent_today(db)
    per_category = settings.collect_display * settings.groq_tokens_per_article

    try:
        for category in targets:
            if spent + per_category > settings.groq_daily_token_budget:
                # 남은 예산으로 이 카테고리를 다 돌 수 없으면 여기서 멈춘다. 중간에
                # 한도에 걸려 절반만 요약된 상태로 끝나는 것보다 경계가 분명하다.
                result.skipped_over_budget.append(category)
                continue

            cmd, cwd = _resolve_command(category)
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=settings.collect_timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                result.failed.append((category, "TIMEOUT"))
                log_error(
                    db,
                    job_id=job_id,
                    error_code="COLLECT_TIMEOUT",
                    message=f"{category}: {settings.collect_timeout_seconds}초 초과",
                )
                continue

            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or "").strip()[-500:]
                result.failed.append((category, f"exit={proc.returncode}"))
                log_error(
                    db,
                    job_id=job_id,
                    error_code="COLLECT_FAILED",
                    message=f"{category}: exit={proc.returncode} {tail}",
                )
                continue

            result.succeeded.append(category)
            spent += per_category
            result.estimated_tokens += per_category

        # 서브프로세스가 **다른 커넥션**으로 INSERT했다. InnoDB는 REPEATABLE READ라
        # 지금 트랜잭션의 스냅샷에는 그 행들이 안 보인다 — `expire_all()`로 ORM 캐시만
        # 비워서는 소용이 없고(스냅샷은 그대로다), 커밋해서 트랜잭션을 끝내야 다음 읽기가
        # 새 스냅샷을 뜬다. 이걸 빼면 신규 기사 수가 항상 0으로 보인다.
        db.commit()
        result.articles_created = max(0, _article_count(db) - before)

        if result.skipped_over_budget:
            log_error(
                db,
                job_id=job_id,
                level="WARN",
                error_code="TOKEN_BUDGET_EXCEEDED",
                message=(
                    f"예산 초과로 {len(result.skipped_over_budget)}개 카테고리 건너뜀 "
                    f"(추정 사용 {spent}/{settings.groq_daily_token_budget})"
                ),
            )

        finish_job(
            db,
            job_id=job_id,
            status=result.status,
            success_count=len(result.succeeded),
            fail_count=len(result.failed),
            detail={
                "slot": slot,
                "provider": settings.collect_provider,
                "display": settings.collect_display,
                "attempted": len(result.attempted),
                "succeeded": len(result.succeeded),
                "failed": result.failed,
                "skipped_over_budget": result.skipped_over_budget,
                "articles_created": result.articles_created,
                "estimated_tokens": result.estimated_tokens,
            },
        )
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        log_error(db, job_id=job_id, error_code="COLLECT_FAILED", message=str(exc))
        finish_job(db, job_id=job_id, status="FAILED")
        db.commit()
        raise
