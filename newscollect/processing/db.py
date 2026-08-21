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


def _lookup_source_id(cursor, provider: str) -> int | None:
    cursor.execute("SELECT id FROM news_sources WHERE name = %s", (provider,))
    row = cursor.fetchone()
    if row is None:
        print(f"[db] news_sources에 '{provider}' 없음 (seed_mock.sql 적용 확인)", file=sys.stderr)
        return None
    return row[0]


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


def _insert_translation(cursor, summary_id: int, item) -> None:
    summary_ko = getattr(item, "summary_ko", None)
    if not summary_ko or summary_ko.startswith(TRANSLATION_FAILURE_PREFIX):
        return

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
    """
    conn = pymysql.connect(**_db_config(), autocommit=False)
    try:
        with conn.cursor() as cur:
            source_ids = {p: _lookup_source_id(cur, p) for p in ("naver", "freenews")}
            tag_id = _lookup_tag_id(cur, category)

        for item in items:
            try:
                with conn.cursor() as cur:
                    article_id = _upsert_article(cur, item, source_ids.get(item.provider))
                    if article_id is None:
                        conn.commit()
                        continue

                    if tag_id is not None:
                        _link_article_tag(cur, article_id, tag_id)

                    result = _upsert_summary(cur, article_id, item)
                    if result is not None:
                        summary_id, is_new = result
                        _insert_translation(cur, summary_id, item)
                        if is_new:
                            _insert_summary_review(cur, summary_id, category)
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"[db] '{item.title[:30]}...' 저장 실패: {e}", file=sys.stderr)
    finally:
        conn.close()

    return items
