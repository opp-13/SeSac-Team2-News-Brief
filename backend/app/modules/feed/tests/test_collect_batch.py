"""수집 배치의 순수 로직: 슬롯 로테이션 + 예산 가드.

서브프로세스 호출은 여기서 검증하지 않는다 — 실제 수집기를 돌려야 하고, 그건 외부 API와
Groq 비용이 걸린다. 대신 "어떤 카테고리를 언제 돌릴지"와 "예산을 넘기지 않는지"라는
결정 부분만 함수 단위로 고정한다 (CLAUDE.md §7 배치는 실행기 없이 테스트 가능해야 한다).
"""

import pytest

from app.batch import collect

SLOTS = ["0700", "1200", "1700"]


def _slugs(n: int) -> list[str]:
    return [f"c{i:02d}" for i in range(n)]


def test_every_category_runs_exactly_once_per_day():
    """63개가 3슬롯에 정확히 한 번씩 배정된다 — 빠지거나 겹치는 카테고리가 없다."""
    slugs = _slugs(63)
    parts = [collect.categories_for_slot(slugs, s, SLOTS) for s in SLOTS]

    assert [len(p) for p in parts] == [21, 21, 21]

    flat = [c for p in parts for c in p]
    assert sorted(flat) == sorted(slugs)   # 누락 없음
    assert len(flat) == len(set(flat))     # 중복 없음


def test_slot_categories_are_spread_not_sliced():
    """이웃한 슬러그가 한 슬롯에 몰리지 않는다.

    슬러그는 알파벳순이라 앞에서 잘라 나누면 'mental health'/'motor sports'/'movies'가
    한 슬롯에 몰려 그 시간대 피드가 한쪽 주제로 쏠린다.
    """
    slugs = _slugs(9)
    first = collect.categories_for_slot(slugs, "0700", SLOTS)

    assert first == ["c00", "c03", "c06"]  # 앞에서 자르면 c00,c01,c02가 됐을 것
    assert first != slugs[:3]


def test_unknown_slot_runs_everything():
    """수동 실행은 전체를 돈다 — 조용히 빈 목록을 받아 아무것도 안 하면 안 된다."""
    slugs = _slugs(63)

    assert collect.categories_for_slot(slugs, "MANUAL", SLOTS) == slugs


@pytest.mark.parametrize("count", [0, 1, 62, 64])
def test_rotation_never_drops_a_category(count):
    """카테고리 수가 슬롯 수로 나누어떨어지지 않아도 전부 배정된다."""
    slugs = _slugs(count)
    flat = [c for s in SLOTS for c in collect.categories_for_slot(slugs, s, SLOTS)]

    assert sorted(flat) == sorted(slugs)


def test_daily_budget_fits_the_measured_cost():
    """설계 근거를 숫자로 고정한다 — display를 올리면 이 테스트가 먼저 깨진다.

    실측: freenews 본문 요약 802~1,003 토큰/건. max_tokens 절단을 고치면 늘어나므로
    1,200으로 잡았다. 63개 × display 2 = 126건.
    """
    from app.core.config import get_settings

    s = get_settings()
    daily_articles = 63 * s.collect_display
    estimated = daily_articles * s.groq_tokens_per_article

    assert daily_articles == 126
    assert estimated <= s.groq_daily_token_budget, (
        f"하루 추정 {estimated} 토큰이 한도 {s.groq_daily_token_budget}을 넘는다 — "
        "COLLECT_DISPLAY를 낮추거나 카테고리를 줄여야 한다"
    )
    # 재시도·추정 오차용 여유가 남아 있어야 한다.
    assert estimated / s.groq_daily_token_budget < 0.85


# ── 수집기가 쓴 status를 래퍼가 가리지 않는다 ──────────────────────────

@pytest.mark.parametrize(
    "recorded,wrapper,expected",
    [
        (None, "SUCCESS", "SUCCESS"),        # 수집기가 아직 아무것도 안 씀
        ("SUCCESS", "PARTIAL", "PARTIAL"),   # 카테고리 하나가 아예 못 돌았다
        ("PARTIAL", "SUCCESS", "PARTIAL"),   # 회귀 방지: 기사 실패가 가려지면 안 된다
        ("FAILED", "PARTIAL", "FAILED"),
        ("PARTIAL", "FAILED", "FAILED"),
        ("RUNNING", "SUCCESS", "SUCCESS"),   # 미완료 상태는 판정에 끼지 않는다
    ],
)
def test_wrapper_does_not_mask_collector_status(recorded, wrapper, expected):
    """래퍼(카테고리 단위)와 수집기(기사 단위)가 같은 행의 status를 각자 쓴다.

    래퍼가 무조건 덮으면, 카테고리가 전부 성공했어도 그 안에서 url 없는 기사가 버려진
    경우가 SUCCESS로 보인다. 둘 중 더 나쁜 쪽이 남아야 한다.
    """
    assert collect._worse_status(recorded, wrapper) == expected


def test_collect_task_ref_is_derived_not_passed():
    """수집기와 래퍼가 반드시 같은 batch_jobs 행을 가리켜야 한다.

    호출자가 task_ref를 넘길 수 있으면 COLLECT 행이 둘로 갈린다(래퍼 것 + 수집기 것).
    run()의 시그니처에 task_ref가 없어야 그 사고가 구조적으로 불가능하다.
    """
    import inspect

    assert "task_ref" not in inspect.signature(collect.run).parameters
