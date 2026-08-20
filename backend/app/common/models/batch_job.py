"""batch_jobs / job_logs 모델 (공용 영역).

세 모듈(A 수집, B 요약·번역, C 큐레이션·보관)이 모두 이 테이블에 쓴다. 그래서 특정
모듈의 `models/`가 아니라 공용에 둔다 — 모듈별로 각자 정의하면 같은 테이블에 서로 다른
매핑이 생긴다.

[SCHEMA-CHECK] 컬럼은 `docs/db/schema.sql` V1.1 기준이다. ENUM 값을 코드에 문자열로
쓰되 SQLAlchemy Enum 타입으로 박지 않았다 — 스키마 V2 제안(`docs/db/schema-v2-proposal.md`)이
검토 중이라 값이 바뀔 수 있고, 마이그레이션은 C 창구를 거쳐야 한다 (§5 규칙 6).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntType


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    # ENUM('COLLECT','SUMMARIZE','TRANSLATE','FEED','RETENTION')
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # ENUM('0700','1200','1700','MANUAL')
    slot: Mapped[str] = mapped_column(String(10), nullable=False, default="MANUAL")
    task_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    # ENUM('PENDING','RUNNING','SUCCESS','PARTIAL','FAILED')
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="PENDING")
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JobLog(Base):
    __tablename__ = "job_logs"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigIntType, ForeignKey("batch_jobs.id"), nullable=False)
    article_id: Mapped[int | None] = mapped_column(BigIntType, nullable=True)
    # ENUM('INFO','WARN','ERROR')
    level: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
