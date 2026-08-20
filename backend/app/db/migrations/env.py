"""Alembic 실행 환경 (C 소유 — 팀 전체의 스키마 창구).

접속 정보는 `alembic.ini`가 아니라 `app.core.config`의 `DATABASE_URL`에서 읽는다.
커밋되는 파일에 시크릿을 넣지 않기 위함이다 (CLAUDE.md §7).

**autogenerate 사용 시 주의 — 모델이 스키마 전체를 덮지 않는다.**
`docs/db/schema.sql`(V2)에는 17개 테이블이 있지만 SQLAlchemy 모델이 있는 것은 그중
일부뿐이다. A(collector)와 B(ai)의 테이블(`collection_filters`, `summary_reviews`,
`ai_invocations`, `cost_budgets`, `cost_alerts`, `retention_policies`)은 아직 모델이 없다.
그대로 autogenerate를 돌리면 **"메타데이터에 없으니 지워라"는 DROP TABLE이 쏟아진다.**
아래 `include_object`가 메타데이터에 없는 테이블을 비교 대상에서 제외해 이 사고를 막는다.
A·B가 모델을 추가하면 이 파일의 import 목록에 함께 등록한다.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base

# --- 모델 import (테이블을 Base.metadata에 등록시키는 것이 목적) -------------------
# 여기에 없는 모델은 autogenerate가 보지 못한다. 모델을 새로 만들면 반드시 추가한다.
from app.common.models.batch_job import BatchJob, JobLog  # noqa: F401,E402
from app.modules.auth.models.user import User  # noqa: F401,E402
from app.modules.feed.models.feed_item import FeedItem  # noqa: F401,E402
from app.modules.feed.models.read_only import (  # noqa: F401,E402
    Article,
    ArticleTag,
    NewsSource,
    Summary,
    Translation,
)
from app.modules.feed.models.tag import Tag, UserTag  # noqa: F401,E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):  # noqa: ANN001, ANN201, ARG001
    """모델이 없는 테이블은 비교 대상에서 뺀다.

    reflected(=DB에는 있는데 메타데이터에 없는) 테이블을 autogenerate가 DROP 대상으로
    잡는 것을 막는다. A·B 소유 테이블이 여기에 해당한다.
    """
    if type_ == "table" and reflected and name not in target_metadata.tables:
        return False
    return True


def run_migrations_offline() -> None:
    """DB 연결 없이 SQL 스크립트만 뽑는다 (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
