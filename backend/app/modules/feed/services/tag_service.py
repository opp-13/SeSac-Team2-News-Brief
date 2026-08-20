"""관심 태그 등록·조회·삭제."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.common.exceptions import NotFoundError
from app.modules.feed.models.tag import Tag, UserTag


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


def replace_user_tags(db: Session, user_id: int, tag_ids: list[int]) -> list[Tag]:
    unique_ids = list(dict.fromkeys(tag_ids))
    if unique_ids:
        found = set(db.scalars(select(Tag.id).where(Tag.id.in_(unique_ids))))
        missing = [t for t in unique_ids if t not in found]
        if missing:
            raise NotFoundError(f"TAG_NOT_FOUND: {missing}")

    db.execute(delete(UserTag).where(UserTag.user_id == user_id))
    db.add_all([UserTag(user_id=user_id, tag_id=tag_id) for tag_id in unique_ids])
    db.flush()
    return list_user_tags(db, user_id)


def remove_user_tag(db: Session, user_id: int, tag_id: int) -> None:
    result = db.execute(
        delete(UserTag).where(UserTag.user_id == user_id, UserTag.tag_id == tag_id)
    )
    if result.rowcount == 0:
        raise NotFoundError("USER_TAG_NOT_FOUND")
    db.flush()
