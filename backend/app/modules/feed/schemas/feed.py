"""피드 응답 스키마 (임시 필드명).

[PROVISIONAL] 필드명·null 규칙·페이지네이션 형태 모두 D의 `docs/api-contracts/feed.md`가 기준.
계약과 다르면 이 파일을 계약에 맞춘다.

요약이 없는 기사는 응답에서 제외하거나 상태값으로 반환한다. **조회 시점에 생성하지 않는다.**
"""

from datetime import datetime

from app.modules.feed.schemas.base import ApiModel


class FeedItemResponse(ApiModel):  # [PROV-F11]
    # 게스트 목록은 feed_items 행이 없으므로 null이다 (docs/api-contracts/feed.md 이중 모드).
    # 프런트가 기사를 식별할 때는 article_id를 쓰고, 북마크에만 feed_item_id가 필요하다.
    feed_item_id: int | None
    article_id: int
    title: str
    press: str | None
    published_at: datetime
    language: str
    # 저장된 요약이 없으면 null. 이 경우 프런트는 상태값으로 처리한다(생성 요청 아님).
    summary: str | None
    summary_type: str | None
    original_url: str  # [PROV-F12] 원문 링크 제공 (필드명 D 확인 필요)
    # 행의 태그 칩용. 매칭된 태그가 맨 앞에 온다. 게스트는 빈 배열(design_plan §7).
    tags: list[str] = []
    # 게스트 필터 칩이 쓰는 카테고리 이름. 매핑이 없으면 null.
    category: str | None = None


class FeedListResponse(ApiModel):  # [PROV-F13]
    # [PROV-F05] 커서 기반으로 임시 구현. D가 offset/page 방식을 확정하면 교체한다.
    items: list[FeedItemResponse]
    next_cursor: int | None = None
    has_next: bool = False


class FeedDetailResponse(ApiModel):  # [PROV-F14]
    feed_item_id: int
    article_id: int
    title: str
    press: str | None
    published_at: datetime
    language: str
    original_url: str
    one_line_summary: str | None = None
    three_line_summary: str | None = None
    detail_summary: str | None = None
