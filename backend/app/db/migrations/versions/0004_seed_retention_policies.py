"""보관 정책 기본값 시드

`retention_policies`는 관리자 화면이 읽고 보관 배치가 참조하는 설정 테이블인데, 행이 하나도
없어서 화면이 빈 목록이었고 배치는 코드 상수를 쓰고 있었다. 대상별 기본 보관 기간을 넣는다.

기간 값은 초기 기본값일 뿐이고, 확정 정책은 관리자 화면에서 바꾼다.
`ARTICLES`는 hard delete(요약·번역·피드가 함께 사라진다)라 가장 길게 잡았다.

Revision ID: 0004_seed_retention
Revises: 0003_drop_cost
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_seed_retention"
down_revision: str | None = "0003_drop_cost"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (target_entity, 기본 보관 일수)
POLICIES = [
    ("ARTICLES", 365),      # hard delete — 요약·번역·피드가 연쇄 삭제된다
    ("SUMMARIES", 365),
    ("TRANSLATIONS", 365),
    ("FEED_ITEMS", 90),     # 큐레이션이 언제든 다시 만든다
    ("LOGS", 30),
]


def upgrade() -> None:
    conn = op.get_bind()
    stmt = sa.text(
        """
        INSERT INTO retention_policies (target_entity, retention_days, strategy, is_active)
        VALUES (:target, :days, 'BATCH_DELETE', TRUE)
        ON DUPLICATE KEY UPDATE retention_days = retention_days
        """
    )
    for target, days in POLICIES:
        conn.execute(stmt, {"target": target, "days": days})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM retention_policies WHERE target_entity IN :targets").bindparams(
            sa.bindparam("targets", value=[t for t, _ in POLICIES], expanding=True)
        )
    )
