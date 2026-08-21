"""Persists collected/summarized items into the real MySQL schema
(docs/shared/schema-v2-proposal branch's schema_no_index.sql: articles,
article_tags, summaries, translations, summary_reviews).

This module only writes to the DB -- it does not call the summarizer.
main.py runs summarize_and_translate.summarize_stage(items) as its own
pipeline stage (filling item.summary / item.summary_ko) before handing
items to persist_stage() here.

`tags` and `news_sources` are seeded separately (see seed_mock.sql) --
this module only looks them up, never inserts into them.
"""

import os
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from hashlib import sha256

import pymysql

from processing import batch_log

SUMMARY_FAILURE_PREFIX = "(요약 실패:"
TRANSLATION_FAILURE_PREFIX = "(번역 실패:"

# Keep in sync with processing/summarize_and_translate.py's GROQ_MODEL.
# Not imported from there on purpose -- db.py doesn't depend on that module
# (main.py owns calling the summarizer; this module only writes to MySQL).
#
# provider/model_name are two columns, not one `model_id` (schema V2, CLAUDE.md
# §8-10): provider is who was called, model_name is what actually answered.
_SUMMARY_PROVIDER = "groq"
_GROQ_MODEL = "openai/gpt-oss-20b"

# Keep in sync with processing/translate.py -- that's the stage that actually
# fills item.title_ko/summary_ko before persist_stage runs (it overwrites
# whatever summarize_and_translate.summarize_item() set, since it runs after).
_TRANSLATE_PROVIDER = "google"
_TRANSLATE_MODEL_NAME = "googletrans"


def _db_config() -> dict:
    return {
        "host": os.environ.get("DB_HOST", "127.0.0.1"),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "news_ai"),
    }


def _url_hash(url: str) -> str:
    """SHA-256 of the URL. No normalization beyond whitespace-stripping (out of scope)."""
    return sha256(url.strip().encode()).hexdigest()


def _parse_published_at(raw: str) -> datetime:
    """naver uses RFC-822 ("Wed, 19 Aug 2026 14:40:00 +0900"), freenews uses
    ISO-8601 with a trailing "Z" ("2026-08-19T04:45:16.000Z")."""
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _has_real_content(text: str | None) -> bool:
    """False for None/empty or the "(...)" error placeholders that
    naver_news/article.py and details/*.py store in `body` on failure."""
    return bool(text) and not text.startswith("(")


def _upsert_source_id(cursor, item) -> int | None:
    """기사의 **언론사**를 news_sources에서 찾고, 없으면 만든다.

    `item.provider`("naver"/"freenews")가 아니라 `item.source`(언론사명)로 찾는다.
    스키마 주석이 그 자리를 이렇게 정의한다 -- 테이블은 '언론사/뉴스 공급자'이고
    `name`은 언론사명, `provider`는 수집 방식('NEWS_API'/'RSS')이다.

    이전에는 provider로 찾아서 모든 기사가 'naver'/'freenews' 행 하나에 매달렸고,
    피드 배지에 신문사 대신 수집 경로가 떴다. Free News API는 언론사(publisher)와
    기자(authors)를 따로 주므로 섞을 이유가 없다.

    조회가 아니라 upsert인 이유: 언론사는 수집하면서 계속 늘어난다. 미리 시드해 둘 수
    있는 목록이 아니다. `uk_sources_name(name)` UNIQUE가 중복을 막는다.
    """
    name = (getattr(item, "source", None) or "").strip()
    if not name:
        # 언론사를 모르면 NULL로 둔다. 'unknown' 같은 가짜 행을 만들지 않는다 --
        # articles.source_id는 NULL 허용이고, 피드는 배지를 비운다.
        return None

    cursor.execute(
        """
        INSERT INTO news_sources (name, provider, language)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
        """,
        (name[:100], "NEWS_API", (getattr(item, "language", None) or "ko")[:5]),
    )
    return cursor.lastrowid


def _category_slug(category: str) -> str:
    """providers/base.py의 CATEGORIES 값을 tags.slug 형태로 정규화한다.

    Free News API의 topic은 공백을 포함한다("internet security") -- slug는 하이픈이다.
    """
    return category.strip().lower().replace(" ", "-")


def _lookup_tag_id(cursor, category: str) -> int | None:
    """카테고리를 slug로 매칭한다.

    name이 아니라 slug로 찾는 이유: name은 화면에 보이는 표시명이라 한국어이고 바뀔 수도
    있다. slug는 변하지 않는 기계 키라, 표시명을 바꿔도 기사-태그 연결이 끊기지 않는다.
    태그 어휘는 backend의 Alembic 리비전 0002_seed_tags가 소유한다.

    is_active는 보지 않는다 -- 비활성 태그는 "화면에 안 보인다"는 뜻이지
    "태깅하지 않는다"가 아니다. 데이터는 쌓아 두고 노출만 고른다.
    """
    slug = _category_slug(category)
    cursor.execute("SELECT id FROM tags WHERE tag_type = 'CATEGORY' AND slug = %s", (slug,))
    row = cursor.fetchone()
    if row is None:
        print(
            f"[db] tags에 slug='{slug}' 없음 (alembic upgrade head 적용 확인)",
            file=sys.stderr,
        )
        return None
    return row[0]


def _upsert_article(cursor, item, source_id: int | None) -> int | None:
    if not item.url:
        print(f"[db] url 없음, 저장 skip: {item.title[:50]}", file=sys.stderr)
        return None

    cursor.execute(
        """
        INSERT INTO articles
            (source_id, url, url_hash, title, content, language, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
        """,
        (
            source_id,
            item.url,
            _url_hash(item.url),
            item.title,
            item.body if _has_real_content(item.body) else None,
            item.language,
            _parse_published_at(item.published_at),
        ),
    )
    return cursor.lastrowid


def _link_article_tag(cursor, article_id: int, tag_id: int) -> None:
    cursor.execute(
        """
        INSERT INTO article_tags (article_id, tag_id)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE relevance = relevance
        """,
        (article_id, tag_id),
    )


def _upsert_summary(cursor, article_id: int, item) -> tuple[int, bool] | None:
    if not item.summary or item.summary.startswith(SUMMARY_FAILURE_PREFIX):
        print(f"[db] article {article_id} 요약 실패 사유: {item.summary!r}", file=sys.stderr)
        cursor.execute("UPDATE articles SET status = 'FAILED' WHERE id = %s", (article_id,))
        return None

    cursor.execute(
        """
        INSERT INTO summaries
            (article_id, summary_type, content, language, provider, model_name, review_status)
        VALUES (%s, 'THREE_LINE', %s, %s, %s, %s, 'PENDING')
        ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
        """,
        (
            article_id,
            item.summary,
            item.language,
            _SUMMARY_PROVIDER,
            _GROQ_MODEL,
        ),
    )
    summary_id = cursor.lastrowid
    # id = LAST_INSERT_ID(id) reassigns id to its own current value, so MySQL
    # reports 0 affected rows on the duplicate-key path (not 2) -- only a
    # fresh INSERT reports 1.
    is_new = cursor.rowcount == 1

    cursor.execute("UPDATE articles SET status = 'SUMMARIZED' WHERE id = %s", (article_id,))
    return summary_id, is_new


def _insert_translation(cursor, summary_id: int, item) -> str:
    """'DONE' | 'FAILED' | 'SKIPPED' 를 돌려준다.

    이전에는 셋 다 조용히 return이었다. 번역이 **필요 없는 것**(원문이 이미 한국어라
    summary_ko가 None)과 **실패한 것**을 구분해야 단계 집계가 맞는다 -- 한국어 기사를
    번역 실패로 세면 화면이 매 실행 실패로 보인다.
    """
    summary_ko = getattr(item, "summary_ko", None)
    if summary_ko and summary_ko.startswith(TRANSLATION_FAILURE_PREFIX):
        return "FAILED"
    if not summary_ko:
        return "SKIPPED"

    title_ko = getattr(item, "title_ko", None)
    if not title_ko or title_ko.startswith(TRANSLATION_FAILURE_PREFIX):
        title_ko = None

    cursor.execute(
        """
        INSERT INTO translations
            (summary_id, target_language, translated_title, translated_content,
             provider, model_name, status)
        VALUES (%s, 'ko', %s, %s, %s, %s, 'DONE')
        ON DUPLICATE KEY UPDATE
            translated_title = VALUES(translated_title),
            id = LAST_INSERT_ID(id)
        """,
        (summary_id, title_ko, summary_ko, _TRANSLATE_PROVIDER, _TRANSLATE_MODEL_NAME),
    )
    cursor.execute(
        "UPDATE articles SET status = 'TRANSLATED' WHERE id = "
        "(SELECT article_id FROM summaries WHERE id = %s)",
        (summary_id,),
    )
    return "DONE"


def _insert_summary_review(cursor, summary_id: int, category: str) -> None:
    cursor.execute(
        """
        INSERT INTO summary_reviews (summary_id, reviewer_id, verdict, note)
        VALUES (%s, NULL, 'OMISSION', %s)
        """,
        (summary_id, f"tag: {category}"),
    )


def persist_stage(items: list, category: str) -> list:
    """Write items (with .summary/.summary_ko already filled in by main.py)
    into articles / article_tags / summaries / translations / summary_reviews.
    Tolerant of per-item failures -- one bad item doesn't stop the batch.

    단계별 결과(`batch_jobs`)와 실패 원인(`job_logs`)도 여기서 남긴다. 요약·번역은 이미
    앞 단계에서 끝났지만 그 성패가 item에 문자열 접두사로 실려 오므로(`(요약 실패: ...)`),
    세 단계 결과를 한 자리에서 집계할 수 있는 곳이 여기다 -- 단계마다 따로 DB에 붙으면
    커넥션이 늘고 부분 실패 시 이력이 서로 어긋난다.
    """
    slot, day = batch_log.resolve_run()
    tally = {
        batch_log.COLLECT: [0, 0, 0],  # [target, success, fail]
        batch_log.SUMMARIZE: [0, 0, 0],
        batch_log.TRANSLATE: [0, 0, 0],
    }
    # (job_type, error_code, 메시지) -- job_logs에 남긴다. 실패 "건수"만으로는 왜 실패했는지
    # 알 수 없고, 관리자 화면의 오류 드로어가 보여줄 것이 바로 이 사유다.
    failures: list[tuple[str, str, str]] = []

    conn = pymysql.connect(**_db_config(), autocommit=False)
    try:
        with conn.cursor() as cur:
            tag_id = _lookup_tag_id(cur, category)

        for item in items:
            tally[batch_log.COLLECT][0] += 1
            try:
                with conn.cursor() as cur:
                    article_id = _upsert_article(cur, item, _upsert_source_id(cur, item))
                    if article_id is None:
                        # url이 없어 저장을 건너뛴 경우. 수집 실패로 센다.
                        tally[batch_log.COLLECT][2] += 1
                        failures.append(
                            (batch_log.COLLECT, "NO_URL", f"{item.title[:60]}: url 없음")
                        )
                        conn.commit()
                        continue
                    tally[batch_log.COLLECT][1] += 1

                    if tag_id is not None:
                        _link_article_tag(cur, article_id, tag_id)

                    tally[batch_log.SUMMARIZE][0] += 1
                    result = _upsert_summary(cur, article_id, item)
                    if result is None:
                        tally[batch_log.SUMMARIZE][2] += 1
                        failures.append(
                            (
                                batch_log.SUMMARIZE,
                                "SUMMARY_FAILED",
                                f"{item.title[:60]}: {(item.summary or '요약 없음')[:200]}",
                            )
                        )
                    else:
                        tally[batch_log.SUMMARIZE][1] += 1
                        summary_id, is_new = result
                        verdict = _insert_translation(cur, summary_id, item)
                        if verdict != "SKIPPED":
                            # 원문이 이미 한국어면 번역 대상이 아니다 -- target에도 넣지
                            # 않는다. 넣으면 한국어 기사만 수집한 슬롯이 "번역 0/N"으로 보인다.
                            tally[batch_log.TRANSLATE][0] += 1
                            idx = 1 if verdict == "DONE" else 2
                            tally[batch_log.TRANSLATE][idx] += 1
                            if verdict == "FAILED":
                                failures.append(
                                    (
                                        batch_log.TRANSLATE,
                                        "TRANSLATION_FAILED",
                                        f"{item.title[:60]}: "
                                        f"{(getattr(item, 'summary_ko', '') or '')[:200]}",
                                    )
                                )
                        if is_new:
                            _insert_summary_review(cur, summary_id, category)
                conn.commit()
            except Exception as e:
                conn.rollback()
                tally[batch_log.COLLECT][2] += 1
                failures.append((batch_log.COLLECT, "PERSIST_FAILED", f"{item.title[:60]}: {e}"))
                print(f"[db] '{item.title[:30]}...' 저장 실패: {e}", file=sys.stderr)

        _record_run(conn, slot=slot, day=day, tally=tally, failures=failures, category=category)
    finally:
        conn.close()

    return items


def _record_run(conn, *, slot, day, tally, failures, category: str) -> None:
    """단계 집계와 실패 원인을 기록한다.

    이력 기록이 실패해도 수집 자체를 죽이지 않는다 -- 기사는 이미 저장됐고, 그걸 되돌리는
    것이 이력 한 줄보다 비싸다. 대신 조용히 넘기지 않고 stderr에 남긴다.
    """
    try:
        with conn.cursor() as cur:
            job_ids = {
                job_type: batch_log.record_stage(
                    cur,
                    job_type=job_type,
                    slot=slot,
                    day=day,
                    target=counts[0],
                    success=counts[1],
                    fail=counts[2],
                )
                for job_type, counts in tally.items()
            }
            for job_type, error_code, message in failures:
                batch_log.log(
                    cur,
                    # 실패를 일으킨 **단계의** 행에 붙인다. 전부 COLLECT에 몰아넣으면
                    # 화면에서 요약 실패가 수집 실패처럼 보인다.
                    job_id=job_ids[job_type],
                    level="ERROR",
                    error_code=error_code,
                    message=f"[{category}] {message}",
                )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[db] 배치 이력 기록 실패: {e}", file=sys.stderr)
