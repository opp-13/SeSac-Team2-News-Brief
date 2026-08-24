"""슬롯 단위 수집 오케스트레이터 -- 컨테이너 내부 cron이 이 스크립트를 부른다.

카테고리 선택(슬롯별 stride 분배)과 Groq 하루 예산 체크는 원래
`backend/app/batch/collect.py`(C 소유)가 자기 ORM으로 계산하고, subprocess로
`main.py`를 호출했다. newscollect가 별도 컨테이너로 떨어지면서 그 경로(같은
파일시스템에서의 subprocess 호출)를 쓸 수 없어 이 스크립트로 옮겼다 -- 로직은
그대로 포팅했고, DB 접근만 backend ORM 대신 이 프로젝트가 이미 쓰던 pymysql
raw 쿼리로 바꿨다.

실행 이력(batch_jobs/job_logs) 기록은 옮길 필요가 없다 -- `main.py`가 호출하는
`processing/db.py`의 `persist_stage()`가 BATCH_SLOT/BATCH_DATE 환경변수만으로
이미 스스로 기록한다 (`processing/batch_log.py`). 이 스크립트는 그 두 환경변수를
채워주는 역할만 한다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime, timezone

import pymysql

SLOTS = ["0700", "1200", "1700"]


def _db_config() -> dict:
    return {
        "host": os.environ.get("DB_HOST", "127.0.0.1"),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "news_ai"),
    }


def category_slugs(conn) -> list[str]:
    """수집 대상 카테고리 슬러그 전체.

    `is_active`로 거르지 않는다 -- 그 값은 화면 노출 여부일 뿐이고, 수집기는 비활성
    태그로도 태깅한다 (CLAUDE.md §8-16).
    """
    with conn.cursor() as cur:
        cur.execute("SELECT slug FROM tags WHERE tag_type = 'CATEGORY' ORDER BY slug")
        return [row[0] for row in cur.fetchall()]


def categories_for_slot(slugs: list[str], slot: str, slots: list[str]) -> list[str]:
    """이 슬롯이 맡을 카테고리. 앞에서 자르지 않고 stride(`[i::n]`)로 흩는다.

    (backend/app/batch/collect.py의 categories_for_slot과 동일한 로직 -- 슬러그가
    알파벳순이라 앞에서 자르면 이웃한 주제가 한 슬롯에 몰린다.)
    """
    if slot not in slots or not slots:
        return list(slugs)
    return slugs[slots.index(slot) :: len(slots)]


def tokens_spent_today(conn, tokens_per_article: int) -> int:
    """오늘 이미 쓴 Groq 토큰 추정치 (건수 × 건당 추정치, 항상 과소 추정)."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM summaries WHERE DATE(created_at) = %s", (date.today(),))
        count = cur.fetchone()[0]
    return int(count or 0) * tokens_per_article


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SLOTS:
        print(f"usage: run_slot.py <{'|'.join(SLOTS)}>", file=sys.stderr)
        return 2
    slot = sys.argv[1]

    provider = os.environ.get("COLLECT_PROVIDER", "freenews")
    display = int(os.environ.get("COLLECT_DISPLAY", "2"))
    language = os.environ.get("COLLECT_LANGUAGE", "en")
    timeout_seconds = int(os.environ.get("COLLECT_TIMEOUT_SECONDS", "300"))
    daily_budget = int(os.environ.get("GROQ_DAILY_TOKEN_BUDGET", "200000"))
    tokens_per_article = int(os.environ.get("GROQ_TOKENS_PER_ARTICLE", "1200"))
    per_category = display * tokens_per_article

    conn = pymysql.connect(**_db_config())
    try:
        slugs = category_slugs(conn)
        targets = categories_for_slot(slugs, slot, SLOTS)
        spent = tokens_spent_today(conn, tokens_per_article)
    finally:
        conn.close()

    print(f"[run_slot] slot={slot} targets={len(targets)} spent~={spent}/{daily_budget}")

    env = dict(os.environ)
    env["BATCH_SLOT"] = slot
    env["BATCH_DATE"] = datetime.now(timezone.utc).date().isoformat()

    failed: list[str] = []
    skipped: list[str] = []
    for category in targets:
        if spent + per_category > daily_budget:
            print(f"[run_slot] {category}: 예산 초과로 건너뜀 (추정 사용 {spent}/{daily_budget})")
            skipped.append(category)
            continue

        cmd = [
            sys.executable,
            "main.py",
            "--category",
            category,
            "--provider",
            provider,
            "--display",
            str(display),
            "--language",
            language,
            "--with-body",
        ]
        try:
            proc = subprocess.run(cmd, env=env, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            print(f"[run_slot] {category}: {timeout_seconds}초 초과", file=sys.stderr)
            failed.append(category)
            continue

        if proc.returncode != 0:
            print(f"[run_slot] {category}: exit={proc.returncode}", file=sys.stderr)
            failed.append(category)
            continue

        spent += per_category

    succeeded = len(targets) - len(failed) - len(skipped)
    print(
        f"[run_slot] 완료 -- 성공 {succeeded}/{len(targets)}, "
        f"실패 {failed}, 예산초과 건너뜀 {len(skipped)}건"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
