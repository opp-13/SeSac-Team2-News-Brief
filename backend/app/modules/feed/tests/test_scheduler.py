"""배치 스케줄러: 슬롯 계산과 중복 실행 방지.

스케줄러 자체(APScheduler)는 테스트하지 않는다 — 라이브러리 동작이다.
검증 대상은 **우리가 정한 규칙**이다: 설정의 슬롯을 언제로 바꾸는가, 오프셋이 자정을
넘어갈 때 어떻게 되는가, 같은 슬롯이 두 번 실행되지 않는가.
"""


from app.batch.scheduler import _acquire_lock, _slot_to_time, build_scheduler
from app.core.config import get_settings


def test_slot_string_becomes_schedule_time():
    assert _slot_to_time("0700") == (7, 0)
    assert _slot_to_time("1200") == (12, 0)
    assert _slot_to_time("1730") == (17, 30)


def test_scheduler_registers_two_jobs_per_slot():
    """슬롯마다 수집 트리거 1개 + C 배치 1개."""
    settings = get_settings()
    # 기동하지 않고 등록 결과만 본다 — start()하면 이벤트 루프가 필요하다.
    scheduler = build_scheduler()
    ids = {job.id for job in scheduler.get_jobs()}
    for slot in settings.batch_slots:
        assert f"collect_{slot}" in ids
        assert f"curate_{slot}" in ids


def test_curate_offset_wraps_past_midnight(monkeypatch):
    """오프셋이 시간을 넘기면 시(hour)가 함께 넘어가야 한다.

    23:50 슬롯 + 30분 오프셋이면 00:20이다. 분만 더하면 23:80이 되어 등록이 실패한다.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "batch_slots", ["2350"])
    monkeypatch.setattr(settings, "curate_offset_minutes", 30)

    scheduler = build_scheduler()
    job = scheduler.get_job("curate_2350")
    fields = {f.name: str(f) for f in job.trigger.fields}
    assert fields["hour"] == "0"
    assert fields["minute"] == "20"


class _FakeRedis:
    """`set(nx=True)`만 흉내 낸다 — 먼저 잡은 쪽만 True."""

    def __init__(self):
        self._keys: set[str] = set()

    def set(self, key, value, nx=False, ex=None):  # noqa: ANN001, ARG002
        if nx and key in self._keys:
            return None
        self._keys.add(key)
        return True


def test_lock_allows_only_the_first_run():
    """같은 슬롯을 두 프로세스가 동시에 잡으면 하나만 통과한다.

    보관 배치가 되돌릴 수 없는 삭제를 하므로, uvicorn 워커가 여럿일 때 중복 실행을
    막아야 한다. 최종 보증은 batch_jobs.task_ref UNIQUE이고 이건 1차 방어다.
    """
    client = _FakeRedis()

    assert _acquire_lock(client, "FEED", "0700") is True
    assert _acquire_lock(client, "FEED", "0700") is False
    # 다른 슬롯은 영향받지 않는다.
    assert _acquire_lock(client, "FEED", "1200") is True


def test_collect_trigger_is_skipped_when_url_unset(caplog):
    """수집 엔드포인트가 미정이면 건너뛴다 — 없는 주소로 매 슬롯 실패 로그를 쌓지 않는다."""
    import asyncio

    from app.batch.scheduler import trigger_collect

    settings = get_settings()
    assert settings.collect_trigger_url is None  # 기본값
    with caplog.at_level("INFO"):
        asyncio.run(trigger_collect("0700"))
    assert "건너뜀" in caplog.text
