"""V2 초기 스키마 — 전체 테이블 생성

`docs/db/schema.sql`(V2)을 그대로 옮긴 초기 리비전이다. 이 리포지토리의 첫 마이그레이션이므로
down_revision 은 None 이고, downgrade() 는 전체 DROP 이다.

**모델이 아니라 schema.sql 을 기준으로 손으로 작성했다.** SQLAlchemy 모델은 아직 스키마의
일부(users / tags / user_tags / news_sources / articles / article_tags / summaries /
translations / feed_items / batch_jobs / job_logs)만 덮고 있어서, autogenerate 로 뽑으면
A·B 소유 테이블 6개(collection_filters, summary_reviews, ai_invocations, cost_budgets,
cost_alerts, retention_policies)가 통째로 빠진다. 스키마의 진실 공급원은 schema.sql 이다
(CLAUDE.md §5 규칙 5).

V1.1 대비 핵심 차이 (schema.sql 헤더 참고):
  - articles 파티셔닝 제거 → PK 는 id 단일, url_hash 유니크가 단일 컬럼으로 정상화
  - article_id FK 복구. articles → summaries / feed_items 는 ON DELETE RESTRICT
  - model_id → provider + model_name 분리, is_token_estimated / is_fallback 추가
  - retention_policies.strategy 에서 PARTITION_DROP 제거, target_entity 에 INVOCATIONS 추가
  - 보조 인덱스(KEY) / FULLTEXT 는 이 리비전에 넣지 않는다. schema.sql 하단의 추가 후보를
    EXPLAIN 으로 확인한 뒤 별도 리비전으로 붙인다.

Revision ID: 0001_v2_initial
Revises:
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0001_v2_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 모든 테이블 공통. utf8mb4 가 아니면 이모지·일부 한자에서 깨진다.
TABLE_KW = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}

NOW = sa.text("CURRENT_TIMESTAMP")

# FK 의존 순서. downgrade 는 이 역순으로 지운다.
_TABLES_IN_ORDER = [
    "users",
    "tags",
    "user_tags",
    "news_sources",
    "batch_jobs",
    "collection_filters",
    "articles",
    "article_tags",
    "job_logs",
    "summaries",
    "translations",
    "summary_reviews",
    "feed_items",
    "ai_invocations",
    "cost_budgets",
    "cost_alerts",
    "retention_policies",
]


def upgrade() -> None:
    # ---------------------------------------------------------------
    # 1. 회원 / 개인화
    # ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nickname", sa.String(50), nullable=False),
        sa.Column(
            "role",
            mysql.ENUM("USER", "ADMIN"),
            nullable=False,
            server_default="USER",
        ),
        sa.Column("preferred_language", sa.CHAR(5), nullable=False, server_default="ko"),
        sa.Column(
            "default_summary_type",
            mysql.ENUM("ONE_LINE", "THREE_LINE", "DETAIL"),
            nullable=False,
            server_default="THREE_LINE",
        ),
        sa.Column(
            "status",
            mysql.ENUM("ACTIVE", "DORMANT", "WITHDRAWN"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uk_users_email"),
        comment="회원. 세션 자체는 Redis, 영속 정보만 MySQL",
        **TABLE_KW,
    )

    op.create_table(
        "tags",
        sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("tag_type", mysql.ENUM("CATEGORY", "KEYWORD"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uk_tags_slug"),
        comment="카테고리/키워드 통합 태그 마스터",
        **TABLE_KW,
    )

    op.create_table(
        "user_tags",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("tag_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column(
            "priority",
            mysql.TINYINT(unsigned=True),
            nullable=False,
            server_default=sa.text("5"),
            comment="큐레이션 가중치 1~10",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tag_id", name="uk_user_tags"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_tags_user", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name="fk_user_tags_tag", ondelete="CASCADE"
        ),
        comment="사용자 관심 태그",
        **TABLE_KW,
    )

    # ---------------------------------------------------------------
    # 2. 수집
    # ---------------------------------------------------------------
    op.create_table(
        "news_sources",
        sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, comment="NEWS_API / RSS 등"),
        sa.Column("api_endpoint", sa.String(500), nullable=True),
        sa.Column("country", sa.CHAR(2), nullable=True),
        sa.Column("language", sa.CHAR(5), nullable=False, server_default="ko"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uk_sources_name"),
        comment="언론사/뉴스 공급자",
        **TABLE_KW,
    )

    op.create_table(
        "batch_jobs",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column(
            "job_type",
            mysql.ENUM("COLLECT", "SUMMARIZE", "TRANSLATE", "FEED", "RETENTION"),
            nullable=False,
        ),
        sa.Column(
            "slot",
            mysql.ENUM("0700", "1200", "1700", "MANUAL"),
            nullable=False,
            server_default="MANUAL",
        ),
        sa.Column(
            "task_ref",
            sa.String(64),
            nullable=True,
            comment="배치 실행기 식별자. 중복 실행 방지용",
        ),
        sa.Column(
            "status",
            mysql.ENUM("PENDING", "RUNNING", "SUCCESS", "PARTIAL", "FAILED"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "target_count", mysql.INTEGER(unsigned=True), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "success_count",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "fail_count", mysql.INTEGER(unsigned=True), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_ref", name="uk_jobs_task_ref"),
        comment="배치 실행 단위(1일 3회 고정). 실행 기술 무관",
        **TABLE_KW,
    )

    op.create_table(
        "collection_filters",
        sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column(
            "source_id",
            mysql.INTEGER(unsigned=True),
            nullable=True,
            comment="NULL이면 전체 소스 대상",
        ),
        sa.Column("filter_type", mysql.ENUM("KEYWORD", "CATEGORY", "PRESS"), nullable=False),
        sa.Column("value", sa.String(200), nullable=False),
        sa.Column(
            "is_include",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
            comment="TRUE=포함, FALSE=제외",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["news_sources.id"], name="fk_filters_source", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_filters_admin", ondelete="SET NULL"
        ),
        comment="수집 대상 필터링 규칙",
        **TABLE_KW,
    )

    op.create_table(
        "articles",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("source_id", mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column("collect_job_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column(
            "url_hash",
            sa.CHAR(64),
            nullable=False,
            comment="SHA-256(정규화 URL). 중복 제거 기준",
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", mysql.LONGTEXT(), nullable=True),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("language", sa.CHAR(5), nullable=False, server_default="ko"),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column(
            "status",
            mysql.ENUM("COLLECTED", "SUMMARIZED", "TRANSLATED", "FAILED"),
            nullable=False,
            server_default="COLLECTED",
        ),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        # V2에서 파티셔닝을 제거해 단일 컬럼 유니크로 돌아왔다. V1.1은 파티션 키를 포함해야
        # 해서 (url_hash, published_at) 복합이었고, published_at만 달라지면 중복이 통과했다.
        sa.UniqueConstraint("url_hash", name="uk_articles_url_hash"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["news_sources.id"], name="fk_articles_source", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["collect_job_id"], ["batch_jobs.id"], name="fk_articles_job", ondelete="SET NULL"
        ),
        comment="원문 기사",
        **TABLE_KW,
    )

    op.create_table(
        "article_tags",
        sa.Column("article_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("tag_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column(
            "relevance", sa.Numeric(4, 3), nullable=False, server_default=sa.text("1.000")
        ),
        sa.PrimaryKeyConstraint("article_id", "tag_id"),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], name="fk_article_tags_article", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], name="fk_article_tags_tag", ondelete="CASCADE"
        ),
        comment="기사-태그 매핑. 큐레이션 매칭 기준",
        **TABLE_KW,
    )

    op.create_table(
        "job_logs",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("job_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("article_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column(
            "level", mysql.ENUM("INFO", "WARN", "ERROR"), nullable=False, server_default="INFO"
        ),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "retry_count", mysql.TINYINT(unsigned=True), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["batch_jobs.id"], name="fk_logs_job", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], name="fk_logs_article", ondelete="SET NULL"
        ),
        comment="수집/처리 오류 및 재시도 로그",
        **TABLE_KW,
    )

    # ---------------------------------------------------------------
    # 3. AI 요약 / 번역 (다중 프로바이더)
    # ---------------------------------------------------------------
    op.create_table(
        "summaries",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("article_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column(
            "summary_type", mysql.ENUM("ONE_LINE", "THREE_LINE", "DETAIL"), nullable=False
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.CHAR(5), nullable=False, server_default="ko"),
        sa.Column(
            "provider", sa.String(50), nullable=False, comment="openai / anthropic / google 등"
        ),
        sa.Column("model_name", sa.String(100), nullable=False, comment="호출 시점의 실제 모델"),
        sa.Column("prompt_version", sa.String(20), nullable=False, server_default="v1"),
        sa.Column(
            "review_status",
            mysql.ENUM("PENDING", "OK", "FLAGGED"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "summary_type", name="uk_summaries"),
        # RESTRICT: 요약이 남아 있으면 원문 삭제를 막는다. 원문은 URL로 재수집할 수 있지만
        # 요약은 LLM을 다시 호출해야 하므로, 보관 배치가 원문을 지우면서 비용을 태워 만든
        # 결과를 함께 날리는 것을 차단한다.
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], name="fk_summaries_article", ondelete="RESTRICT"
        ),
        comment="LLM 요약 결과 영구 저장. 조회 시 재호출 없이 재사용",
        **TABLE_KW,
    )

    op.create_table(
        "translations",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("summary_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("target_language", sa.CHAR(5), nullable=False),
        sa.Column("translated_title", sa.String(500), nullable=True),
        sa.Column("translated_content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column(
            "status", mysql.ENUM("DONE", "FAILED"), nullable=False, server_default="DONE"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("summary_id", "target_language", name="uk_translations"),
        sa.ForeignKeyConstraint(
            ["summary_id"], ["summaries.id"], name="fk_translations_summary", ondelete="CASCADE"
        ),
        comment="요약문의 다국어 번역 결과",
        **TABLE_KW,
    )

    op.create_table(
        "summary_reviews",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("summary_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("reviewer_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column(
            "verdict",
            mysql.ENUM("OK", "HALLUCINATION", "OMISSION", "OTHER"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["summary_id"], ["summaries.id"], name="fk_reviews_summary", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_reviews_reviewer", ondelete="SET NULL"
        ),
        comment="관리자 환각/누락 검수 이력",
        **TABLE_KW,
    )

    # ---------------------------------------------------------------
    # 4. 배포 (개인화 피드)
    # ---------------------------------------------------------------
    op.create_table(
        "feed_items",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("article_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("summary_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column(
            "translation_id",
            mysql.BIGINT(unsigned=True),
            nullable=True,
            comment="원문 언어와 동일하면 NULL",
        ),
        sa.Column(
            "matched_tag_id",
            mysql.INTEGER(unsigned=True),
            nullable=True,
            comment="이 기사가 노출된 사유",
        ),
        sa.Column("score", sa.Numeric(6, 3), nullable=False, server_default=sa.text("0")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_bookmarked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "article_id", name="uk_feed"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_feed_user", ondelete="CASCADE"
        ),
        # RESTRICT: 원문 삭제로 피드 행이 조용히 사라지지 않게 한다. 피드는 summaries로부터
        # curate 배치가 재생성할 수 있으므로, 정리는 summaries 삭제(→ CASCADE) 경로로만 일어난다.
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], name="fk_feed_article", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["summary_id"], ["summaries.id"], name="fk_feed_summary", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["translation_id"], ["translations.id"], name="fk_feed_trans", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["matched_tag_id"], ["tags.id"], name="fk_feed_tag", ondelete="SET NULL"
        ),
        comment="배치가 미리 만들어 둔 개인화 피드. 조회 시 LLM 미호출",
        **TABLE_KW,
    )

    # ---------------------------------------------------------------
    # 5. 운영 (비용 / 보관)
    # ---------------------------------------------------------------
    op.create_table(
        "ai_invocations",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("job_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("article_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("task_type", mysql.ENUM("SUMMARIZE", "TRANSLATE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column(
            "input_tokens", mysql.INTEGER(unsigned=True), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "output_tokens",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_token_estimated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="프로바이더가 토큰 수를 주지 않아 추정한 경우 TRUE",
        ),
        sa.Column(
            "cost_usd",
            sa.Numeric(10, 6),
            nullable=False,
            server_default=sa.text("0"),
            comment="호출 시점 단가로 계산한 값을 그대로 보존",
        ),
        sa.Column("latency_ms", mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column(
            "is_fallback",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
            comment="기본 모델 실패로 대체 모델이 처리한 경우 TRUE",
        ),
        sa.Column(
            "status",
            mysql.ENUM("SUCCESS", "FAILED", "TIMEOUT", "RATE_LIMITED"),
            nullable=False,
            server_default="SUCCESS",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["batch_jobs.id"], name="fk_inv_job", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["article_id"], ["articles.id"], name="fk_inv_article", ondelete="SET NULL"
        ),
        comment="LLM 호출 단위 비용/사용량 추적",
        **TABLE_KW,
    )

    op.create_table(
        "cost_budgets",
        sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("period_type", mysql.ENUM("DAILY", "MONTHLY"), nullable=False),
        sa.Column("threshold_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column("threshold_calls", mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column(
            "notify_channel", sa.String(100), nullable=False, comment="slack webhook / email 등"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        # 기간 유형별 예산은 하나만 유지. 프로바이더별 예산이 필요해지면 provider 컬럼을
        # 추가하고 UNIQUE(period_type, provider)로 넓힌다 (CLAUDE.md §8 미결, B 담당).
        sa.UniqueConstraint("period_type", name="uk_budgets_period"),
        comment="비용/호출 임계치 설정",
        **TABLE_KW,
    )

    op.create_table(
        "cost_alerts",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("budget_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column(
            "actual_cost", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "actual_calls",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("is_notified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("triggered_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["budget_id"], ["cost_budgets.id"], name="fk_alerts_budget", ondelete="CASCADE"
        ),
        comment="임계치 초과 알림 이력",
        **TABLE_KW,
    )

    op.create_table(
        "retention_policies",
        sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column(
            "target_entity",
            mysql.ENUM(
                "ARTICLES", "SUMMARIES", "TRANSLATIONS", "FEED_ITEMS", "LOGS", "INVOCATIONS"
            ),
            nullable=False,
        ),
        sa.Column("retention_days", mysql.INTEGER(unsigned=True), nullable=False),
        # V1.1의 PARTITION_DROP은 제거했다. 파티셔닝을 뺐으므로 실행 불가능한 값이고,
        # ENUM에 남겨 두면 관리자 화면의 선택지로 노출돼 배치가 런타임에 실패한다.
        sa.Column(
            "strategy",
            mysql.ENUM("BATCH_DELETE"),
            nullable=False,
            server_default="BATCH_DELETE",
        ),
        sa.Column("last_executed_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_entity", name="uk_retention_target"),
        comment="데이터 보관 기간/TTL 정책",
        **TABLE_KW,
    )


def downgrade() -> None:
    # FK 의존 역순으로 지운다. 순서를 바꾸면 FK 제약에 걸려 실패한다.
    for table in reversed(_TABLES_IN_ORDER):
        op.drop_table(table)
