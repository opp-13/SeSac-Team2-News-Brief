"""C가 **읽기 전용**으로 참조하는 테이블 매핑 (articles/news_sources=A 소유,
summaries/translations=B 소유).

- 이 모델들로 INSERT/UPDATE 하지 않는다. 조회 전용이다.
- **DELETE 예외는 보관 정책 배치 하나뿐이다.** 데이터 보관은 CLAUDE.md §3에서 C 담당으로
  명시돼 있고, V2가 `articles` → `summaries`를 `RESTRICT`로 묶어 두었기 때문에 요약을 먼저
  지우지 않으면 원문을 지울 수 없다. 그래서 `services/retention_service.py`만 `Article` /
  `Summary`를 DELETE 한다. 그 파일 밖에서는 하지 않는다.
- A/B 모듈 폴더에서 직접 import 하는 것은 금지(CLAUDE.md §5-3)이므로 최소 컬럼만 재선언했다.
- [TODO-SHARED] 여러 모듈이 같은 테이블을 읽으므로 최종적으로는 공용 모델로 승격하는 것이
  맞다. 공용 영역이라 팀에 알리고 옮겨야 해서, 합의 전까지 이 파일을 쓴다.

컬럼명은 `docs/db/schema.sql`(V2)을 기준으로 맞췄다. 이전 정의에는 스키마에 없는 컬럼이
있어(articles.press, translations.content) MySQL에서는 조회가 실패했다. 언론사 이름은
articles가 직접 갖고 있지 않고 news_sources를 조인해서 얻는다.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntType


class NewsSource(Base):
    """언론사/뉴스 공급자 (A 소유). articles.source_id가 이 테이블을 가리킨다."""

    __tablename__ = "news_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # C는 읽지 않지만 스키마상 NOT NULL이고 DEFAULT가 없다. 빼 두면 로컬 시드가
    # MySQL에서 "Field 'provider' doesn't have a default value"로 깨진다.
    provider: Mapped[str] = mapped_column(String(50))  # NEWS_API / RSS 등


class Article(Base):
    __tablename__ = "articles"

    # V2에서 파티셔닝을 제거해 PK가 id 단일로 돌아왔다. V1.1은 published_at 월 단위
    # 파티셔닝 때문에 PK가 (id, published_at) 복합이어야 했고(파티션 키는 모든 UNIQUE/PK에
    # 포함되어야 한다), 복합 PK는 자동 증가를 쓸 수 없어 테스트·시드가 id를 직접 박아야 했다.
    # 이제 그 제약이 없다.
    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    source_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("news_sources.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    # 중복 제거 기준(SHA-256(정규화 URL)). 쓰기 소유자는 A지만 NOT NULL + DEFAULT 없음이라
    # 모델에 없으면 INSERT가 불가능하다. V2에서 이 컬럼 단독 UNIQUE가 되면서 비로소
    # 중복 방어가 실제로 동작한다 (CLAUDE.md §8-3).
    url_hash: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(5), default="ko")
    status: Mapped[str] = mapped_column(String(20))


class ArticleTag(Base):
    """기사-태그 매핑 (A 소유). 게스트 피드의 카테고리 필터와 행의 태그 칩에 쓴다.

    프런트는 카테고리/태그를 **이름**으로 다루므로(`docs/api-contracts/feed.md`)
    이 매핑 없이는 게스트 필터 칩과 태그 칩을 채울 수 없다.
    """

    __tablename__ = "article_tags"

    article_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    # RESTRICT: 요약이 남아 있으면 원문 삭제 자체가 실패한다. 원문은 재수집할 수 있지만
    # 요약은 LLM을 다시 호출해야 만들어지므로, 보관 배치가 원문을 지우면서 비용을 태워 만든
    # 결과를 연쇄 삭제하는 경로를 스키마가 막는다 (schema.sql V2 [삭제 순서]).
    article_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("articles.id", ondelete="RESTRICT"), index=True
    )
    summary_type: Mapped[str] = mapped_column(String(20))  # ONE_LINE | THREE_LINE | DETAIL
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(5), default="ko")
    # V2에서 model_id가 provider + model_name으로 분리됐다. 둘 다 NOT NULL이라 모델에
    # 없으면 INSERT가 불가능하다. 쓰기 소유자는 B이고 C는 읽기만 한다.
    provider: Mapped[str] = mapped_column(String(50))  # openai / anthropic / google 등
    model_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    summary_id: Mapped[int] = mapped_column(
        BigIntType, ForeignKey("summaries.id", ondelete="CASCADE"), index=True
    )
    target_language: Mapped[str] = mapped_column(String(5))
    translated_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 스키마 컬럼명은 translated_content다. 이전 모델은 content로 선언해 있었다.
    translated_content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), default="DONE")
    created_at: Mapped[datetime] = mapped_column(DateTime)
