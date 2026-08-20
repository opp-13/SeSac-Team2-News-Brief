"""데이터 보관 정책 로직.

실행기 비의존. 보관 기간은 설정으로 외부화하며 코드에 상수로 박지 않는다.
되돌릴 수 없는 삭제이므로 항상 건수를 반환해 배치 로그로 남긴다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.feed.models.feed_item import FeedItem

# [OPEN] 실제 보관 기간은 요구사항 명세서 기준으로 확정 후 설정(app.core.config)으로 이동.
DEFAULT_FEED_ITEM_RETENTION_DAYS = 90


@dataclass
class RetentionResult:
    cutoff: datetime
    deleted_feed_items: int
    dry_run: bool


def run_retention(
    db: Session,
    *,
    retention_days: int = DEFAULT_FEED_ITEM_RETENTION_DAYS,
    dry_run: bool = False,
    now: datetime | None = None,
) -> RetentionResult:
    """보관 기간이 지난 feed_items를 정리한다.

    articles/summaries 정리는 A·B 소유 데이터이므로 여기서 지우지 않는다.
    (기사 원본 보관 정책은 파티셔닝 vs FK 미결 사항과 함께 확정 후 별도 처리)
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)

    target_ids = list(db.scalars(select(FeedItem.id).where(FeedItem.created_at < cutoff)))
    if dry_run or not target_ids:
        return RetentionResult(cutoff=cutoff, deleted_feed_items=len(target_ids), dry_run=dry_run)

    db.execute(delete(FeedItem).where(FeedItem.id.in_(target_ids)))
    db.flush()
    return RetentionResult(cutoff=cutoff, deleted_feed_items=len(target_ids), dry_run=False)
