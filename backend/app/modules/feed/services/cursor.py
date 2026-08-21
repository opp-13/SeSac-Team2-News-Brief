"""피드 커서 인코딩.

목록은 `published_at DESC, id DESC`로 정렬한다. 그래서 커서도 그 두 값을 함께 담아야 한다 —
`id`만으로는 이어서 읽을 수 없다. 수집 순서(id)와 발행 순서(published_at)가 다르기 때문이다.
실제로 시드에서는 id 1이 가장 최신이라, id 기준 정렬은 오래된 기사를 맨 위에 올렸다.

커서는 **프런트가 파싱하지 않는 불투명 문자열**이다 (`docs/api-contracts/feed.md`).
base64로 감싸는 것은 암호화가 아니라, 내부 표현이 바뀌어도 프런트가 영향을 받지 않게
하려는 것이다.
"""

import base64
import json
from datetime import datetime

from app.common.exceptions import BadRequestError


def encode(published_at: datetime, row_id: int) -> str:
    payload = json.dumps(
        {"p": published_at.isoformat(), "i": row_id}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode(raw: str) -> tuple[datetime, int]:
    """실패하면 INVALID_CURSOR(400). 계약에 정의된 오류다."""
    try:
        padded = raw + "=" * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
        return datetime.fromisoformat(data["p"]), int(data["i"])
    except Exception as exc:  # noqa: BLE001 — 어떤 형태로 깨졌든 사용자에겐 같은 오류다
        raise BadRequestError("INVALID_CURSOR") from exc


def encode_run(executed_at: datetime, run_key: str) -> str:
    """배치 실행 이력용 커서.

    피드와 달리 run은 `(날짜, slot)`으로 묶은 **집계 행**이라 정수 id가 없다. 그래서
    tie-breaker로 run 키 문자열(`20260821-0700`)을 쓴다. 같은 executed_at을 갖는 run이
    둘 나오는 일은 사실상 없지만, 커서가 그 경우에 무한 루프가 되지 않게 키를 함께 담는다.
    """
    payload = json.dumps(
        {"t": executed_at.isoformat(), "k": run_key}, separators=(",", ":")
    )
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_run(raw: str) -> tuple[datetime, str]:
    """실패하면 INVALID_CURSOR(400) — 피드 커서와 같은 오류 코드다."""
    try:
        padded = raw + "=" * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
        return datetime.fromisoformat(data["t"]), str(data["k"])
    except Exception as exc:  # noqa: BLE001 — 어떤 형태로 깨졌든 사용자에겐 같은 오류다
        raise BadRequestError("INVALID_CURSOR") from exc
