"""C가 **읽기 전용**으로 참조하는 테이블 매핑 (articles=A 소유, summaries/translations=B 소유).

- 이 모델들로 INSERT/UPDATE/DELETE 하지 않는다. 조회 전용이다.
- A/B 모듈 폴더에서 직접 import 하는 것은 금지(CLAUDE.md §5-3)이므로 최소 컬럼만 재선언했다.
- [TODO-SHARED] 여러 모듈이 같은 테이블을 읽으므로 최종적으로는 공용 모델로 승격하는 것이
  맞다. 공용 영역 변경이라 별도 PR + 전원 리뷰 대상 → 팀 합의 전까지 이 파일을 쓴다.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    press: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(Integer, index=True)
    summary_type: Mapped[str] = mapped_column(String(20))  # ONE_LINE | THREE_LINE | DETAIL
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary_id: Mapped[int] = mapped_column(Integer, index=True)
    target_language: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
