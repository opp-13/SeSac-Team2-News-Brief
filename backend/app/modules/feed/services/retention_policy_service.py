"""보관 정책 조회·수정 (관리자 화면용).

계약: `docs/api-contracts/admin.md`의 `GET /admin/retention`,
`PATCH /admin/retention/{targetEntity}`.

`target_entity`가 유일 키라 그 값이 곧 식별자다 — 별도 id를 API에 노출하지 않는다.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestError, NotFoundError
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import Article, Summary, Translation
from app.modules.feed.models.retention_policy import RetentionPolicy

# target_entity → 건수를 셀 테이블. 화면의 recordCount가 이 값이다.
_COUNT_SOURCES = {
    "ARTICLES": Article,
    "SUMMARIES": Summary,
    "TRANSLATIONS": Translation,
    "FEED_ITEMS": FeedItem,
}


@dataclass
class PolicyView:
    """API 응답 1건. 스키마 행 + 파생값(record_count)."""

    policy: RetentionPolicy
    record_count: int


def _count_for(db: Session, target_entity: str) -> int:
    """대상 테이블의 현재 행 수.

    [성능] 정확한 COUNT(*)를 쓴다. 계약(`admin.md`)은 대량 테이블에서
    `information_schema.TABLES.TABLE_ROWS` 근사치를 쓰는 안도 제시했지만, 지금 규모
    (일 수천 건)에서는 COUNT(*)가 충분히 빠르고 근사치의 오차가 오히려 혼란스럽다.
    수백만 행이 되면 근사치 + `recordCountApproximate` 플래그로 바꾼다.

    LOGS는 job_logs로 공용 모델(`app.common.models`)에 있어 여기서 세지 않는다 —
    C의 서비스가 공용 모델을 끌어오면 의존이 뒤집힌다. 0으로 응답하고, 필요해지면
    공용 쪽에 건수 조회를 두고 호출한다.
    """
    model = _COUNT_SOURCES.get(target_entity)
    if model is None:
        return 0
    return db.scalar(select(func.count()).select_from(model)) or 0


def list_policies(db: Session) -> list[PolicyView]:
    policies = list(
        db.scalars(select(RetentionPolicy).order_by(RetentionPolicy.target_entity))
    )
    return [PolicyView(policy=p, record_count=_count_for(db, p.target_entity)) for p in policies]


def update_policy(
    db: Session,
    *,
    target_entity: str,
    retention_days: int | None = None,
    is_active: bool | None = None,
) -> PolicyView:
    """부분 수정. 화면이 편집할 수 있는 값은 retention_days와 is_active뿐이다.

    **보관 기간 축소는 되돌릴 수 없는 삭제를 예고한다.** 다음 배치에서 실제로 지워지므로,
    확인 절차(축소 시 삭제 예정 건수 표시 등)는 화면 쪽에서 붙여야 한다
    (`admin.md` "보관 기간 축소는 파괴적 동작이다" — 디자인 승인 대기).
    """
    policy = db.scalar(
        select(RetentionPolicy).where(RetentionPolicy.target_entity == target_entity)
    )
    if policy is None:
        raise NotFoundError("UNKNOWN_RETENTION_TARGET")

    if retention_days is not None:
        if retention_days <= 0:
            raise BadRequestError("INVALID_RETENTION_DAYS")
        policy.retention_days = retention_days
    if is_active is not None:
        policy.is_active = is_active

    db.flush()
    return PolicyView(policy=policy, record_count=_count_for(db, policy.target_entity))
