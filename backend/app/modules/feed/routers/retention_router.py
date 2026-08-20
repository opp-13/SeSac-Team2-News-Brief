"""관리자 보관 정책 라우터.

로직은 services에 둔다 — 여기는 입출력과 의존성 주입만 (SKILL §4-4).
"""

from fastapi import APIRouter, Depends

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_admin
from app.modules.auth.models.user import User
from app.modules.feed import api_paths
from app.modules.feed.schemas.retention import (
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
)
from app.modules.feed.services import retention_policy_service

retention_router = APIRouter(
    prefix=api_paths.ADMIN_RETENTION_PREFIX, tags=["admin-retention"]
)


def _to_response(view) -> RetentionPolicyResponse:  # noqa: ANN001
    p = view.policy
    return RetentionPolicyResponse(
        target_entity=p.target_entity,
        retention_days=p.retention_days,
        strategy=p.strategy,
        is_active=p.is_active,
        record_count=view.record_count,
        last_executed_at=p.last_executed_at,
    )


@retention_router.get(api_paths.ADMIN_RETENTION_LIST, response_model=list[RetentionPolicyResponse])
def list_retention_policies(
    _admin: User = Depends(get_current_admin), db=Depends(get_db)
) -> list[RetentionPolicyResponse]:
    return [_to_response(v) for v in retention_policy_service.list_policies(db)]


@retention_router.patch(
    api_paths.ADMIN_RETENTION_UPDATE, response_model=RetentionPolicyResponse
)
def update_retention_policy(
    target_entity: str,
    body: RetentionPolicyUpdateRequest,
    _admin: User = Depends(get_current_admin),
    db=Depends(get_db),
) -> RetentionPolicyResponse:
    view = retention_policy_service.update_policy(
        db,
        target_entity=target_entity,
        retention_days=body.retention_days,
        is_active=body.is_active,
    )
    db.commit()
    return _to_response(view)
