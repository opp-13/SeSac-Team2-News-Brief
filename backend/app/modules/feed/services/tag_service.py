"""관심 태그 등록·조회·삭제.

관심 태그를 바꾸면 그 사용자의 피드를 **즉시 다시 채운다**(`replace_user_tags` 참고).
`feed_items`는 배치가 미리 만들어 두는 테이블이라, 트리거가 없으면 가입 직후·태그 변경
직후에 피드가 빈 채로 남는다.
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.common.exceptions import NotFoundError
from app.modules.auth.models.user import User  # 같은 담당(C) 소유 모듈이므로 참조 허용
from app.modules.feed.models.tag import Tag, UserTag
from app.modules.feed.services import curation_service


def list_all_tags(db: Session) -> list[Tag]:
    return list(db.scalars(select(Tag).order_by(Tag.name)))


def list_user_tags(db: Session, user_id: int) -> list[Tag]:
    stmt = (
        select(Tag)
        .join(UserTag, UserTag.tag_id == Tag.id)
        .where(UserTag.user_id == user_id)
        .order_by(Tag.name)
    )
    return list(db.scalars(stmt))


def replace_user_tags(db: Session, user: User, tag_ids: list[int]) -> tuple[list[Tag], int]:
    """관심 태그를 통째로 교체하고, 바뀐 관심사로 피드를 다시 채운다.

    반환값은 (교체된 태그 목록, 새로 만들어진 피드 행 수)다.

    **왜 여기서 큐레이션을 부르는가.** `feed_items`는 `curate` 배치만 채우는 테이블인데
    배치 실행 기술이 아직 미정이라(CLAUDE.md §8 미결) 아무것도 배치를 트리거하지 않는다.
    그래서 가입해서 관심 태그를 골라도 피드가 영원히 비어 있었다. 관심사가 바뀌는 순간이
    그 사용자의 피드를 다시 만들 자연스러운 시점이라 여기에 붙였다.

    LLM 호출이 아니라 태그 매칭 DB 조회일 뿐이므로 조회 경로 금지 규칙(CLAUDE.md §1)과는
    무관하다. 후보 기사 수에 상한이 있어(`article_limit`) 응답 시간도 제한된다.
    `curate_for_user`는 이미 있는 행을 건너뛰므로 여러 번 저장해도 중복이 생기지 않는다.

    태그를 **뺐을 때**도 맞춘다. 현재 관심사가 하나도 안 붙은 기사의 행은 지우고, 살아남은
    행의 노출 사유(`matched_tag_id`)는 현재 관심사로 다시 지정한다
    (`curation_service.sync_user_feed`, 계약: `docs/api-contracts/feed.md`).
    """
    unique_ids = list(dict.fromkeys(tag_ids))
    if unique_ids:
        found = set(db.scalars(select(Tag.id).where(Tag.id.in_(unique_ids))))
        missing = [t for t in unique_ids if t not in found]
        if missing:
            raise NotFoundError(f"TAG_NOT_FOUND: {missing}")

    db.execute(delete(UserTag).where(UserTag.user_id == user.id))
    db.add_all([UserTag(user_id=user.id, tag_id=tag_id) for tag_id in unique_ids])
    db.flush()

    synced = curation_service.sync_user_feed(db, user=user)
    return list_user_tags(db, user.id), synced.created


def remove_user_tag(db: Session, user_id: int, tag_id: int) -> None:
    result = db.execute(
        delete(UserTag).where(UserTag.user_id == user_id, UserTag.tag_id == tag_id)
    )
    if result.rowcount == 0:
        raise NotFoundError("USER_TAG_NOT_FOUND")
    db.flush()
