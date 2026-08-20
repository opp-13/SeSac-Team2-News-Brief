# 배치 스케줄러 머지 가이드

> 작성: C 담당  
> 대상 브랜치: `feature/feed/module-skeleton`  
> 관련 파일: `backend/app/batch/scheduler.py`, `backend/app/main.py`

---

## 1. 개요

07:00 / 12:00 / 17:00 슬롯에 A+B 파이프라인을 HTTP로 트리거하고,
30분 오프셋으로 C의 큐레이션·보관 배치를 실행하는 APScheduler 기반 스케줄러.

```
07:00  →  POST {A_COLLECT_ENDPOINT}   (A+B 파이프라인)
07:30  →  run_curation() + run_retention()   (C 배치)
(12:00 / 17:00 동일)
```

---

## 2. 머지 전 필수 작업

### (1) A 담당자 → C 담당자에게 전달 필요

| 항목 | 현재 값 | 확정 후 수정 위치 |
|---|---|---|
| collect 엔드포인트 경로 | `http://localhost:8000/internal/batch/collect` (플레이스홀더) | `backend/app/batch/scheduler.py` — `A_COLLECT_ENDPOINT` |
| 인증 방식 (헤더/토큰 등) | 미정 | `scheduler.py` — `trigger_collect()` httpx 헤더 |
| 응답 방식 (동기/비동기) | 미정 | 동기면 오프셋 제거 후 콜백 방식으로 변경 |

### (2) 공용 스켈레톤 머지 후 수정 필요

| 항목 | 현재 임시 처리 | 교체 대상 |
|---|---|---|
| DB 세션 | `scheduler.py` 내 `_get_db_session()` 직접 생성 | `app.db.session.get_db` |
| DB URL | `scheduler.py` 내 하드코딩 (`DATABASE_URL`) | `app.core.config.settings.DATABASE_URL` |

### (3) requirements.txt 추가 (공용 PR — 전원 리뷰)

```
apscheduler>=3.10
httpx>=0.27
pymysql>=1.1        # MySQL 드라이버 (공용 스켈레톤에 없으면)
```

> `requirements.txt`는 충돌이 잦으므로 rebase 후 즉시 머지 (CLAUDE.md §5-7)

---

## 3. main.py 머지 시 충돌 방지

`main.py`는 공용 파일로 **각 담당자가 라우터를 추가**한다.
머지 순서가 뒤엉키면 라우터 등록이 누락된다.

### C가 등록한 라우터 (이미 포함)

```python
from app.modules.auth.routers.auth_router import router as auth_router
from app.modules.feed.routers.feed_router import router as feed_router
from app.modules.feed.routers.tag_router import my_tag_router, tag_router

app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(tag_router)
app.include_router(my_tag_router)
```

### 다른 담당자가 추가해야 할 라우터

| 담당 | import 경로 | 비고 |
|---|---|---|
| A | `app.modules.collector.routers.*` | A PR에서 추가 |
| B | `app.modules.ai.routers.*` | B PR에서 추가 |

### 충돌 방지 절차

1. 이 브랜치를 `develop`에 **먼저** 머지한다.
2. A·B가 각자 브랜치에서 `develop` rebase 후 라우터를 추가해 PR을 올린다.
3. 각 PR은 `main.py` diff를 반드시 확인한다 — 다른 담당의 라우터가 사라지면 반려.

---

## 4. A 엔드포인트 응답 방식 확정 시 변경 사항

### 현재: 오프셋 방식 (비동기 가정)

```python
# 07:00 collect 트리거, 07:30 curate 실행 (독립 스케줄)
CURATE_OFFSET_MIN = 30
```

### 변경: 동기 방식 (A가 완료 후 응답)

`scheduler.py`의 `trigger_collect()`를 아래와 같이 수정한다.

```python
async def trigger_collect(slot: str) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(A_COLLECT_ENDPOINT, json={"slot": slot})
        resp.raise_for_status()
    # A+B 완료 확인 후 즉시 curate 실행
    await trigger_curate(slot)

# build_scheduler()에서 curate 별도 job 제거
```

---

## 5. 체크리스트 (PR 리뷰어용)

- [ ] `A_COLLECT_ENDPOINT` 가 플레이스홀더에서 실제 경로로 교체됐는가
- [ ] `DATABASE_URL` 이 `app.core.config` 로 교체됐는가 (공용 스켈레톤 머지 후)
- [ ] `requirements.txt` 에 `apscheduler`, `httpx` 추가됐는가
- [ ] `main.py` 에 A·B 라우터가 누락되지 않았는가
- [ ] 스케줄러가 `lifespan` 에 정상 연결됐는가 (`scheduler.start()` / `scheduler.shutdown()`)
