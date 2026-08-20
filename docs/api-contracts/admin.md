# Admin API 계약

> **상태: DRAFT — 승인 대기. 이 문서만 담당이 3명으로 갈린다.**
> 루트 CLAUDE.md §3: "관리자 대시보드가 쓰는 집계 API는 A(파이프라인 현황)와 B(비용/사용량)가
> 각각 제공한다. D는 화면만 담당하되 필요한 응답 형태를 계약으로 먼저 요청한다."
>
> | 섹션 | 제공 담당 |
> |---|---|
> | `/admin/pipeline/*` | **A** (collector — 파이프라인 처리 현황 집계) — 미구현, 프론트는 목업 |
> | ~~`/admin/llm-usage`~~ | 스코프 제외 (§8-17). 화면·테이블 모두 제거됨 |
> | `/admin/retention` | **C** (feed) — ✅ 구현 완료, 프론트 연결됨 |
>
> 관리자 화면은 이제 2개다(파이프라인 / 보관 정책). 보관 정책은 실제 API를 쓰고,
> 파이프라인만 아직 `usePipelineRuns`가 목업 배열을 직접 쓴다.
>
> 관련 문서: [auth.md](auth.md), [feed.md](feed.md), [meta.md](meta.md)

## 공통 규약

- `BASE = /api/v1`, `credentials: 'include'`
- 응답 봉투: `{ "success": true, "data": ... }` | `{ "success": false, "error": { "code", "message" } }`
- 시각은 **ISO 8601 UTC**. 상대시간·숫자 포맷은 프론트 책임 (§ 아래 참고)
- **모든 엔드포인트는 `users.role = 'ADMIN'` 을 요구한다.**
  비관리자 → `403` + `code: "ADMIN_REQUIRED"`, 비로그인 → `401` + `code: "NO_SESSION"`.
  프론트도 `routes/AdminRoute.tsx`에서 `useAuth().isAdmin`으로 한 번 막지만,
  **화면 가드는 보안 경계가 아니므로 서버에서 반드시 다시 검사할 것.**

## ⚠️ 이 문서 전체에 걸친 문제 — 프론트 타입이 프로토타입 유산이다

관리자 화면의 프론트 타입(`frontend/src/types/admin.ts`)은 피그마 프로토타입에서 그대로
이관된 것으로, **서버가 보내주기 어렵거나 보내면 안 되는 값들이 섞여 있다.** 각 섹션에
표시했고, 계약 확정 시 프론트 타입을 고치는 작업(D 담당)이 함께 필요하다.

공통 원칙: **서버는 원시 값(숫자·ISO 시각·enum)만 보내고, 표시용 문자열은 프론트가 만든다.**

---

# 1. 파이프라인 (담당: A)

화면: `/admin/pipeline` — 배치 실행 목록 + 오류 상세 사이드 드로어(폭 480px)

## 🔴 구조적 불일치 — "실행 1건 = 여러 단계" 모델이 스키마에 없다

프론트 화면은 **실행 1건이 5개 단계를 품는 구조**로 그려져 있다
(뉴스 수집 → 중복 제거 → LLM 요약 → 태그 분류 → DB 저장).

그런데 스키마의 `batch_jobs`는 **각 행이 곧 하나의 단계**다:

```sql
job_type ENUM('COLLECT','SUMMARIZE','TRANSLATE','FEED','RETENTION')
slot     ENUM('0700','1200','1700','MANUAL')
```

즉 여러 단계를 묶는 "실행(run)" 개념이 테이블에 없다. 두 가지 길이 있다.

**(a) `slot` + 날짜로 묶어 run으로 취급 — 스키마 변경 없음 (제안)**
같은 날짜·같은 slot의 `batch_jobs` 행들을 하나의 run으로 집계한다.
"하루 3회 고정 배치"라는 요구사항과 `slot` ENUM이 정확히 대응하므로 자연스럽다.
run id는 `20260819-0700` 처럼 날짜+slot으로 합성한다.

**(b) 부모 run 테이블 추가 — 스키마 변경 필요**
정확하지만 루트 CLAUDE.md §5 규칙6에 따라 **C 창구를 거쳐야** 하고 마이그레이션이 필요하다.

→ **(a)를 제안한다.** 아래 응답 예시는 (a) 기준이다.

또한 프로토타입의 단계 이름 5개 중 **`중복 제거`·`태그 분류`·`DB 저장`은 `job_type` ENUM에
없다.** 이 셋은 `COLLECT`/`FEED` 내부의 하위 작업이다. 단계 목록을 `job_type` 기준(최대 5개:
COLLECT/SUMMARIZE/TRANSLATE/FEED/RETENTION)으로 바꿀지, 프로토타입 이름을 유지하려고
집계 로직을 더 넣을지 **A와 합의 필요** — 프론트는 `stages` 배열을 그대로 그리므로
어느 쪽이든 화면은 동작한다.

## GET /admin/pipeline/runs — 실행 이력 목록

### 요청

```
GET /api/v1/admin/pipeline/runs?cursor=...&limit=20
```

커서 기반(루트 CLAUDE.md §6). 최신 실행이 먼저 오고, 아직 실행되지 않은 예정 slot도
포함한다(프로토타입에 `pending` 상태 행이 있음 — "1시간 후" 실행 예정).

### 응답 — 200

```json
{
  "success": true,
  "data": {
    "runs": [
      {
        "id": "20260819-0700",
        "slot": "0700",
        "status": "SUCCESS",
        "executedAt": "2026-08-19T03:00:00Z",
        "processedCount": 231,
        "errorCount": 0,
        "stages": [
          {
            "jobType": "COLLECT",
            "status": "SUCCESS",
            "targetCount": 284,
            "successCount": 231,
            "failCount": 0,
            "startedAt": "2026-08-19T03:00:00Z",
            "finishedAt": "2026-08-19T03:00:42Z"
          }
        ],
        "models": ["claude-sonnet-5"]
      }
    ],
    "nextCursor": null,
    "hasNext": false
  }
}
```

### 필드 매핑

| 필드 | 출처 | 비고 |
|---|---|---|
| `id` | `DATE(created_at)` + `slot` 합성 | (a) 방식 |
| `slot` | `batch_jobs.slot` | |
| `status` | 하위 job들의 `batch_jobs.status` 집계 | 집계 규칙 아래 |
| `executedAt` | 하위 job 중 최소 `started_at` | ISO UTC |
| `processedCount` | 하위 job `success_count` 집계 | 어떻게 집계할지 아래 질문 참고 |
| `errorCount` | 하위 job `fail_count` 합 | |
| `stages[].jobType` | `batch_jobs.job_type` | |
| `stages[].status` | `batch_jobs.status` | |
| `stages[].targetCount` / `successCount` / `failCount` | 동명 컬럼 | |
| `stages[].startedAt` / `finishedAt` | 동명 컬럼 | 소요시간은 프론트가 계산 |
| `models` | `ai_invocations.model_name` DISTINCT (해당 job) | 아래 참고 |
| `providers` | `ai_invocations.provider` DISTINCT (해당 job) | 스키마 V2에서 추가된 컬럼 |

### status 값의 대소문자 — 결정 필요

스키마는 `'SUCCESS' | 'PARTIAL' | 'FAILED' | 'PENDING' | 'RUNNING'`(대문자),
프론트 프로토타입은 `'success' | 'partial' | 'failure' | 'pending'`(소문자, 게다가
`FAILED`가 아니라 `failure`)를 쓴다.

→ **스키마 ENUM 값을 그대로 쓰는 것을 제안한다** (진실 공급원을 둘로 만들지 않기 위해).
채택 시 프론트 매핑 수정 필요(D). `RUNNING`은 프로토타입에 없으니 프론트에 추가해야 한다.

### run 단위 status 집계 규칙 — 결정 필요

하위 job 상태들로 run 상태를 정하는 규칙을 명시해야 한다. 제안:

| 조건 | run status |
|---|---|
| 모든 job `SUCCESS` | `SUCCESS` |
| 하나라도 `RUNNING` | `RUNNING` |
| 모든 job `PENDING` | `PENDING` |
| 일부 실패했으나 일부 성공 / `PARTIAL` 존재 | `PARTIAL` |
| 핵심 단계(COLLECT) 실패로 후속이 모두 건너뜀 | `FAILED` |

### `provider` / `model` 이 `batch_jobs`에 없다

프로토타입 타입은 run마다 `provider: string`, `model: string`을 갖는다. 스키마에는
`batch_jobs`에 모델 정보가 없고, `ai_invocations` / `summaries`에만 있다.

→ 위 예시처럼 `models: string[]` / `providers: string[]`(해당 run의 `ai_invocations`
DISTINCT)로 바꾸는 것을 제안한다. 한 배치에서 모델이 하나만 쓰인다는 보장이 없으므로
배열이 안전하다. 스키마 V2가 `model_id`를 `provider` + `model_name`으로 분리했으므로
서버가 접두사로 파생할 필요 없이 두 컬럼을 그대로 DISTINCT 하면 된다.

## GET /admin/pipeline/runs/{runId}/logs — 오류 상세

화면: 우측 사이드 드로어(폭 480px). design_plan.md §7: "오류 상세는 별도 페이지로 만들지
말고 우측 사이드 드로어로 여세요."

현재 프론트는 드로어에 **하드코딩된 문구**("응답 시간 초과(timeout) 오류. Rate limit 초과로
인한 재시도 실패.")를 보여준다. 실제 로그로 교체해야 한다 — 스키마에 `job_logs`가 이미 있다.

### 요청

```
GET /api/v1/admin/pipeline/runs/20260818-2100/logs?level=ERROR
```

| 파라미터 | 설명 |
|---|---|
| `level` | `INFO` \| `WARN` \| `ERROR` (`job_logs.level`). 생략 = 전체 |

### 응답 — 200

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "4821",
        "jobType": "SUMMARIZE",
        "articleId": "128390",
        "level": "ERROR",
        "errorCode": "TOKEN_LIMIT_EXCEEDED",
        "message": "입력 토큰 한도 초과로 요약을 건너뜀",
        "retryCount": 2,
        "createdAt": "2026-08-18T21:03:14Z"
      }
    ],
    "nextCursor": null,
    "hasNext": false
  }
}
```

`job_logs` 컬럼과 1:1 대응한다(`error_code`, `message`, `retry_count`, `created_at`).
`id` / `articleId`는 `BIGINT UNSIGNED`이므로 **문자열로 직렬화**할 것.

로그가 많을 수 있으니 커서 페이지네이션을 둔다. 프론트는 현재 페이지네이션 UI가 없어
첫 페이지만 표시한다(추가 구현 필요 시 D).

---

## ~~LLM 비용·사용량~~ — 스코프에서 제외됨

**이 화면은 삭제됐다** (루트 CLAUDE.md §8-17). 프로바이더를 Groq 하나로 고정하면서
프로바이더별 비용 비교의 실익이 사라졌고, 화면만 지우고 스키마를 남기면 아무도 쓰지 않는
테이블이 남으므로 `ai_invocations` / `cost_budgets` / `cost_alerts`도 함께 제거했다
(리비전 `0003_drop_cost`).

되살리려면 그 리비전의 downgrade가 테이블을 복구하고, 호출하는 쪽(A/B)이
`ai_invocations`에 기록을 남기는 일이 선행돼야 한다 — 제거 시점에 그 기록이 한 행도
없었다는 점이 이 결정의 근거이기도 했다.

---

## GET /admin/retention — 정책 목록  ✅ 구현됨

### 응답 — 200

```json
{
  "success": true,
  "data": [
    {
      "targetEntity": "ARTICLES",
      "retentionDays": 90,
      "strategy": "BATCH_DELETE",
      "isActive": true,
      "recordCount": 128402,
      "lastExecutedAt": "2026-08-18T18:00:00Z"
    },
    {
      "targetEntity": "LOGS",
      "retentionDays": 30,
      "strategy": "BATCH_DELETE",
      "isActive": true,
      "recordCount": 4820,
      "lastExecutedAt": null
    }
  ]
}
```

### 필드 매핑 (`retention_policies`)

| 필드 | 출처 | 비고 |
|---|---|---|
| `targetEntity` | `target_entity` | ENUM, `uk_retention_target`로 유일 → 이게 곧 식별자 |
| `retentionDays` | `retention_days` | |
| `strategy` | `strategy` | `BATCH_DELETE` 단일값 (V2에서 `PARTITION_DROP` 제거). 프론트는 현재 미표시 |
| `isActive` | `is_active` | 프론트의 "자동 삭제 켜짐/꺼짐" |
| `recordCount` | 대상 테이블 건수 | **스키마에 없는 파생값** — 아래 참고 |
| `lastExecutedAt` | `last_executed_at` | NULL 가능 (한 번도 안 돌았을 때). 프론트는 `—` 표시 |

### ✅ 프론트 목업의 대상 목록 — 스키마 V2에서 해소됨

| 프론트 목업 (`mocks/retentionMockData.ts`) | 스키마 `target_entity` ENUM |
|---|---|
| `articles` | `ARTICLES` ✓ |
| `summaries` | `SUMMARIES` ✓ |
| `logs` | `LOGS` ✓ |
| `llm_calls` (LLM 호출 이력) | **제거됨** — 비용 추적 스코프 제외 (§8-17) |
| — | `TRANSLATIONS` (목업에 없음) |
| — | `FEED_ITEMS` (목업에 없음) |

**스키마 V2가 `target_entity`에 `INVOCATIONS`를 추가했다.** 프론트는 서버가 주는 목록을
그대로 그리도록 만들면 되므로, 목업의 4개 항목은 서버 응답에 맞춰 교체한다(D).
목업에 없던 `TRANSLATIONS` / `FEED_ITEMS`까지 오므로 RetentionPage의 항목 수가 늘어난다.

### ✅ `ARTICLES` 정책은 hard delete다

스키마 V2는 `articles` → `summaries` / `feed_items` FK를 `ON DELETE RESTRICT`로 걸었다.
요약이 남아 있는 기사는 삭제 자체가 실패한다 — 원문은 재수집할 수 있지만 요약은 LLM을 다시
호출해야 만들어지므로, 보관 배치가 원문을 지우면서 비용을 태워 만든 결과를 연쇄 삭제하는
것을 막기 위한 의도적 제약이다 (루트 CLAUDE.md §8-11).

**`ARTICLES` 정책은 hard delete로 확정했다** (§8-14). "요약을 버린다"는 판단을 명시적으로
먼저 내린 뒤 원문을 지운다. 따라서 화면의 "삭제"는 말 그대로 행 삭제이고, `recordCount`도
그대로 "지워질 행 수"를 뜻한다 — 문구를 바꿀 필요는 없다.

**다만 사용자에게 보이지 않는 연쇄가 있다.** `ARTICLES` 정책 1회 실행으로 다음이 함께 사라진다.

| 지워지는 것 | 경로 |
|---|---|
| `summaries` | 배치가 직접 삭제 (원문 삭제의 선행 조건) |
| `translations` | `summaries` 삭제에 FK CASCADE |
| `feed_items` | `summaries` 삭제에 FK CASCADE |
| `article_tags` | `articles` 삭제에 FK CASCADE |

즉 **`ARTICLES` 보관 기간을 줄이면 요약·번역도 같이 날아간다.** 아래 "보관 기간 축소는
파괴적 동작이다" 절의 확인 절차가 `ARTICLES`에서는 특히 중요하다. 서버는 축소 요청 시
삭제 예정 건수를 원문/요약 각각으로 응답할 수 있다(배치가 `dry_run`으로 이미 세고 있다).

### ⚠️ `recordCount` — 성능 주의

`articles`는 대량 테이블이다(V2에서 파티셔닝은 제거했다). 매 조회마다 `COUNT(*)`를 돌리면
관리자 화면 하나가 DB를 부담스럽게 만든다. 대안:

1. `information_schema.TABLES.TABLE_ROWS` 근사치 사용 (빠르지만 부정확)
2. 보관 배치가 실행될 때 집계해 저장 (**스키마 변경** 필요)
3. 응답에서 `recordCount`를 빼고 화면에서도 제거 (**디자인 변경** — 카드 4칸 중 1칸)

→ (1)을 제안하고, 근사치라면 `recordCountApproximate: true` 같은 플래그를 함께 보낼 것.
프론트는 §2의 "추정" 배지와 같은 방식으로 표시할 수 있다.

### 이름·설명 문구는 어디서 오는가 — 결정 필요

프론트는 정책마다 `name`("기사 원문")과 `description`("수집된 원문 HTML 및 텍스트 데이터")을
표시한다. 스키마에는 두 필드가 없다.

- **(a) 프론트 상수로 둔다** — `targetEntity` → 한국어 라벨 매핑을 프론트가 갖는다.
  ENUM이 5개로 고정적이므로 실용적이다. (제안)
- **(b) 서버가 보낸다** — `retention_policies`에 컬럼 추가(스키마 변경).

**(a)로 확정.** `frontend/src/api/admin.ts`가 `targetEntity` → 한국어 라벨 매핑을 갖는다.
서버가 표시 문구를 만들면 문구를 고칠 때마다 백엔드를 배포해야 한다 — 위 "서버는 포맷된
문자열을 보내지 않는다"와 같은 기준이다.

## PATCH /admin/retention/{targetEntity} — 정책 수정  ✅ 구현됨

화면의 "수정 → 저장" 버튼. 이전에는 프론트가 로컬 state만 바꿔서 새로고침하면 초기화됐는데,
이제 실제로 서버에 반영된다. 관리자 권한 필수 — 401(미로그인)과 403(`ADMIN_REQUIRED`)을 구분한다.

### 요청

```
PATCH /api/v1/admin/retention/ARTICLES
{ "retentionDays": 120, "isActive": true }
```

두 필드 모두 선택적(부분 수정 허용). 프론트 화면이 편집할 수 있는 값은 이 둘뿐이다
(`strategy`는 화면에 없음).

### 응답 — 200

수정 후의 정책 1건을 `GET`과 동일한 형태로 반환한다.

### 응답 — 오류

| 상황 | code | HTTP |
|---|---|---|
| 존재하지 않는 `targetEntity` | `UNKNOWN_RETENTION_TARGET` | 404 |
| `retentionDays` 가 0 이하 | `INVALID_RETENTION_DAYS` | 400 |

### ⚠️ 보관 기간 축소는 파괴적 동작이다

`retentionDays`를 줄이면 다음 보관 배치에서 **데이터가 삭제된다.** V2에서 `PARTITION_DROP`이
빠져 전부 `BATCH_DELETE`이므로 파티션 단위로 즉시 날아가는 경로는 없어졌지만, 되돌릴 수 없는
삭제라는 점은 그대로다.

프론트 화면에는 현재 확인 절차가 없다(수정 → 저장 즉시 반영). 아래를 제안한다.

- 서버: 축소 요청 시 삭제 예정 건수를 함께 응답하거나, `confirm: true` 파라미터 요구
- 프론트: 축소일 때 확인 모달 — **디자인에 없는 요소이므로 디자인 담당 승인 필요**

이건 계약보다 정책 결정이 먼저다. **구현 전 합의할 것.**

---

## 열려있는 질문 정리

| # | 질문 | 담당 |
|---|---|---|
| 1 | run 모델 (a) slot+날짜 집계 vs (b) 부모 테이블 추가 | A (+C if 스키마) |
| 2 | 단계 이름을 `job_type` 기준으로 바꿀지, 프로토타입 5단계를 유지할지 | A · D |
| 3 | status 값 대소문자 — 스키마 ENUM 그대로 쓸지 | A · D |
| 4 | run 단위 status 집계 규칙 | A |
| 5 | `processedCount` 집계 방식 (단계별 success_count를 어떻게 하나로 합칠지) | A |
| ~~6~~ | ~~멀티 프로바이더로 갈지, Bedrock 단일로 갈지~~ → **해소.** 스키마 V2가 멀티 프로바이더로 확정 (`provider` + `model_name`) | ~~B · 디자인~~ |
| ~~7~~ | ~~"추정" 플래그 근거 — 컬럼 추가 vs 서버 규칙~~ → **해소.** `ai_invocations.is_token_estimated` 추가 | ~~B (+C if 스키마)~~ |
| ~~8~~ | ~~`ai_invocations`를 보관 정책 대상 ENUM에 추가할지~~ → **해소.** `target_entity`에 `INVOCATIONS` 추가 | ~~C~~ |
| ~~9~~ | ~~`recordCount` 산출 방식~~ → **확정.** 정확한 `COUNT(*)`. 현 규모에서 충분히 빠르고 근사치의 오차가 오히려 혼란스럽다. 수백만 행이 되면 근사치 + `recordCountApproximate`로 전환 | ~~C~~ |
| 10 | 보관 기간 축소 시 확인 절차 | C · 디자인 |
| 11 | 집계 기간의 시간대 기준 (KST vs UTC) — 일별 차트 경계가 달라진다 | A · B |
| ~~12~~ | ~~`ARTICLES` 보관 정책이 soft purge인지 hard delete인지~~ → **해소.** hard delete로 확정 (CLAUDE.md §8-14). 다만 요약·번역이 함께 삭제되므로 축소 확인 절차(10번)와 묶어서 봐야 한다 | ~~C · 디자인~~ |
| 13 | `is_fallback` / `TIMEOUT` · `RATE_LIMITED` 를 화면에 노출할지 | D |
