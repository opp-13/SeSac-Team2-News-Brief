"""태그 라우터 (전체 태그 목록 / 내 관심 태그)."""

from fastapi import APIRouter, Depends, status

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models.user import User
from app.modules.feed import api_paths
from app.modules.feed.schemas.tag import MyTagsReplaceRequest, TagResponse
from app.modules.feed.services import tag_service

tag_router = APIRouter(prefix=api_paths.TAGS_PREFIX, tags=["tags"])
my_tag_router = APIRouter(prefix=api_paths.ME_TAGS_PREFIX, tags=["tags"])


@tag_router.get(api_paths.TAG_LIST, response_model=list[TagResponse])
def list_tags(db=Depends(get_db)):
    return tag_service.list_all_tags(db)


@my_tag_router.get(api_paths.MY_TAG_LIST, response_model=list[TagResponse])
def list_my_tags(user: User = Depends(get_current_user), db=Depends(get_db)):
    return tag_service.list_user_tags(db, user.id)


@my_tag_router.put(api_paths.MY_TAG_REPLACE, response_model=list[TagResponse])
def replace_my_tags(
    body: MyTagsReplaceRequest,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    tags, _created = tag_service.replace_user_tags(db, user, body.tag_ids)
    db.commit()
    return tags


@my_tag_router.delete(api_paths.MY_TAG_DELETE, status_code=status.HTTP_204_NO_CONTENT)
def delete_my_tag(tag_id: int, user: User = Depends(get_current_user), db=Depends(get_db)):
    tag_service.remove_user_tag(db, user.id, tag_id)
    db.commit()
