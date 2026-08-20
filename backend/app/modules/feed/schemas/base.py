"""응답 스키마 공통 베이스.

[PROVISIONAL-NAMING] 현재 응답 필드는 camelCase로 직렬화한다(프런트 관례 가정).
D의 계약 문서가 snake_case로 확정되면 `alias_generator`만 제거하면 전 응답이 바뀐다.
개별 스키마에서 필드명을 하드코딩으로 바꾸지 말 것.

[TODO-SHARED] 동일 클래스가 feed 모듈에도 있다. 계약 확정 후 `app/common`으로 승격
(공용 영역이므로 옮기게 되면 팀에 알린다).
"""

from pydantic import BaseModel, ConfigDict


def to_camel(s: str) -> str:
    head, *tail = s.split("_")
    return head + "".join(w.capitalize() for w in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
