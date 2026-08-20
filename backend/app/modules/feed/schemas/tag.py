"""tag 요청/응답 스키마.

[PROVISIONAL] 필드명은 D의 `docs/api-contracts/feed.md` 확정 전까지 임시값이다.
D 계약 확정 시 이 파일의 필드명만 수정하면 전 계층이 따라간다.
"""

from __future__ import annotations

from pydantic import Field

from app.modules.feed.schemas.base import ApiModel


class TagResponse(ApiModel):
    """태그 1건 응답 (PROV-T11)."""

    id: int
    name: str
    category: str | None = None


class TagListResponse(ApiModel):
    """선택 가능한 전체 태그 목록 응답 (GET /tags)."""

    items: list[TagResponse]


class MyTagListResponse(ApiModel):
    """내 관심 태그 목록 응답 (GET /me/tags)."""

    items: list[TagResponse]


class MyTagsReplaceRequest(ApiModel):
    """관심 태그 전체 교체 요청 (PROV-T12).

    [D 확인 필요] 전체 교체(PUT) 방식으로 임시 구현.
    개별 토글(POST/DELETE) 방식이면 계약 변경 요청 후 수정한다.
    """

    tag_ids: list[int] = Field(default_factory=list)
