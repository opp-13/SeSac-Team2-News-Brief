"""비용 추적 제거 (ai_invocations / cost_budgets / cost_alerts)

팀 결정: 프로바이더를 Groq 하나로 고정하면서 **LLM 호출량·비용 추적을 스코프에서 제외**했다.
화면만 지우고 스키마를 남겨 두면 아무도 쓰지 않는 테이블이 계속 남으므로 함께 지운다
(루트 CLAUDE.md §1 운영 항목에서도 제거).

실제로 이 테이블들은 한 번도 쓰인 적이 없다 — 수집 파이프라인이 Groq를 호출하면서
ai_invocations에 한 행도 남기지 않았고, cost_budgets / cost_alerts는 읽는 코드조차 없었다.

`retention_policies.target_entity`의 `INVOCATIONS`도 함께 제거한다. 가리킬 테이블이
없어지므로 남겨 두면 관리자 화면에 실행 불가능한 항목이 노출된다.

되살리려면 downgrade가 0001과 동일한 정의로 다시 만든다.

Revision ID: 0003_drop_cost
Revises: 0002_seed_tags
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0003_drop_cost"
down_revision: str | None = "0002_seed_tags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_KW = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}
NOW = sa.text("CURRENT_TIMESTAMP")

_TARGET_ENTITY_WITHOUT_INVOCATIONS = mysql.ENUM(
    "ARTICLES", "SUMMARIES", "TRANSLATIONS", "FEED_ITEMS", "LOGS"
)
_TARGET_ENTITY_WITH_INVOCATIONS = mysql.ENUM(
    "ARTICLES", "SUMMARIES", "TRANSLATIONS", "FEED_ITEMS", "LOGS", "INVOCATIONS"
)


def upgrade() -> None:
    # ENUM에서 값을 빼기 전에 그 값을 쓰는 행을 정리한다. 남아 있으면 ALTER가 실패한다.
    op.execute("DELETE FROM retention_policies WHERE target_entity = 'INVOCATIONS'")
    op.alter_column(
        "retention_policies",
        "target_entity",
        existing_type=_TARGET_ENTITY_WITH_INVOCATIONS,
        type_=_TARGET_ENTITY_WITHOUT_INVOCATIONS,
        existing_nullable=False,
    )
    # FK 의존 역순으로 지운다 (cost_alerts -> cost_budgets).
    op.drop_table("cost_alerts")
    op.drop_table("cost_budgets")
    op.drop_table("ai_invocations")


def downgrade() -> None:
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
            "is_token_estimated", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("latency_ms", mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.text("0")),
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
        sa.Column("notify_channel", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("period_type", name="uk_budgets_period"),
        comment="비용/호출 임계치 설정",
        **TABLE_KW,
    )
    op.create_table(
        "cost_alerts",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("budget_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("actual_cost", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
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
    op.alter_column(
        "retention_policies",
        "target_entity",
        existing_type=_TARGET_ENTITY_WITHOUT_INVOCATIONS,
        type_=_TARGET_ENTITY_WITH_INVOCATIONS,
        existing_nullable=False,
    )
