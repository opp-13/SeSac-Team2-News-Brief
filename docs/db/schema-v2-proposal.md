# 스키마 V2 제안 — 검토 요청 (결정 완료, 기록용)

> **상태: 종료.** 여기 적힌 안건은 모두 결정됐고 `docs/db/schema.sql`은 V2로 갱신됐다.
> 확정된 내용은 루트 `CLAUDE.md` §8(9~19번)이 유일한 기준이다. 이 문서는 **왜 그렇게
> 결정했는지**를 남긴 기록이고, 여기 적힌 "결정 필요"는 이미 지난 이야기다.
>
> 결정 결과 요약: C-1 다중 프로바이더 채택(이후 §8-17에서 Groq 단일로 좁히며 비용 추적은
> 스코프 제외) · C-2 파티셔닝 제거 후 FK 유지 · C-3 `cost_budgets` 유니크는 테이블째
> 제거되며 무의미 · D-2 `PARTITION_DROP` 제거 · D-3 헤더에서 라이브러리명 제거 ·
> `ARTICLES` 보관 정책은 hard delete.
>
> 함께 있던 `schema_no_index.sql`은 가져오지 않았다 — 그 파일의 내용이 그대로
> `schema.sql` V2가 됐고, 두 벌을 두면 어느 쪽이 기준인지 갈린다.

> **성격**: 제안서다. `docs/db/schema.sql`(V1.1)은 이 PR에서 건드리지 않았다.
> 아래 [결정 필요 안건](#결정-필요-안건)이 정리된 뒤, **C가 창구가 되어** `schema.sql` 갱신과
> Alembic revision 생성을 진행한다 (루트 `CLAUDE.md` §3, §5 규칙 6).
>
> **제안 파일**: `docs/db/schema_no_index.sql`
> **작성 배경**: 인덱스를 분리해 관리하려고 만든 파일이지만, 검토 과정에서 인덱스 외에
> 세 종류의 변경이 섞여 있음을 확인했다. 그중 둘은 스키마 최적화가 아니라 프로젝트 결정 사항이다.

---

## 1. 변경 분류

| 구분 | 내용 | 성격 | 조치 |
|---|---|---|---|
| **A** | 보조 인덱스 14개 + FULLTEXT 제거 | 성능 튜닝 | 그대로 수용 가능 |
| **B** | `url_hash` 유니크 정상화, `is_token_estimated`, `is_fallback`, `INVOCATIONS`, `TIMEOUT`/`RATE_LIMITED`, `article_id` FK 복구 | 개선 (2건은 버그 수정) | 그대로 수용 권장 |
| **C** | 다중 프로바이더 전환, 파티셔닝 제거, `cost_budgets` 유니크 추가 | **미결 사항 결정** | 합의 필요 |
| **D** | CASCADE 연쇄 삭제 위험, `PARTITION_DROP` 잔존, 헤더 문구 | 신규 파일의 결함 | D-1 반영 완료 / D-2·D-3 결정 필요 |

---

## 2. A — 인덱스 제거 (문제 없음)

제거 대상: `idx_users_status`, `idx_tags_type_active`, `idx_sources_active`, `idx_filters_active`,
`idx_jobs_type_status`, `idx_logs_job`, `idx_logs_created`, `idx_summaries_review`, `idx_inv_created`,
`idx_inv_job`, `idx_alerts_budget`, `idx_feed_list`, `idx_feed_bookmark`, `idx_article_tags_tag`,
`idx_user_tags_tag`, `ft_articles_title`.

전부 조회 성능용이고 업무 규칙이 아니다. 확인한 사항:

- **FK 컬럼은 InnoDB가 인덱스를 자동 생성**한다. 따라서 실제로 사라지는 것은 복합/커버링 인덱스와
  비-FK 단일 인덱스뿐이다. 제안 파일 하단 주석이 이 점을 정확히 명시하고 있다.
- **FULLTEXT 제거는 현재 무해하다.** 프론트에 검색 기능이 아직 없다
  (`frontend/src/components/common/Header.tsx` — 검색 버튼이 `title="검색 (준비 중)"`로 비활성).
  검색을 구현하는 시점에 `ALTER TABLE ... ADD FULLTEXT`로 되돌리면 된다.
- **성능 손실이 가장 큰 것은 `idx_feed_list`다.** 피드 목록은 앱에서 가장 빈번한 쿼리이고,
  `uk_feed(user_id, article_id)`로 `user_id` 필터는 타지만
  `ORDER BY created_at DESC, score DESC`는 filesort가 된다. 일 수천 건 규모에서는 문제 없다.

하단 "성능 튜닝 시 추가할 인덱스" 목록은 원본 인덱스를 빠짐없이 담고 있고,
`idx_articles_published`에 `id DESC`를 덧붙여 커서 페이지네이션까지 반영했다. 원본보다 낫다.

---

## 3. B — 개선 사항

### B-1. `url_hash` 유니크가 이제야 실제로 동작한다 (버그 수정)

V1.1은 파티셔닝 때문에 유니크 키가 복합이어야 했다:

```sql
-- V1.1 (파티셔닝 → 파티션 키를 모든 UNIQUE/PK에 포함해야 함)
UNIQUE KEY uk_articles_url_hash (url_hash, published_at)
```

그 결과 **같은 `url_hash`가 `published_at`만 다르면 중복 INSERT가 통과한다.**
루트 `CLAUDE.md` §8.3의 확정 사항 —

> 중복 제거는 이중 방어로 확정. Redis `dedup:url:{yyyymmdd}` SET으로 INSERT 전 1차 필터링하되,
> **최종 보증은 `articles.url_hash`(정규화 URL의 SHA-256) 유니크 인덱스가 담당한다. Redis만 믿는 구현 금지.**

— 이 원칙이 V1.1 스키마에서는 **구조적으로 지켜지지 않고 있었다.**

빠져나가는 경로는 `published_at`이 달라지는 경우다. 같은 기사의 발행 시각이 재수집 시점에 조금이라도 다르게
오면(언론사의 기사 수정으로 타임스탬프 갱신, API 응답 편차, 수집기의 시각 정규화 차이) 복합 유니크는
서로 다른 행으로 판단해 그대로 INSERT한다. Redis 1차 필터는 `dedup:url:{yyyymmdd}` 키가 날짜 단위이므로
날짜가 바뀐 뒤의 재수집을 막지 못한다. 즉 두 방어선이 같은 지점에서 함께 뚫린다.

제안 파일은 파티셔닝을 제거해 `UNIQUE KEY uk_articles_url_hash (url_hash)`로 되돌렸다. 규칙대로 동작한다.
**A 담당(collector)에게 직접 영향이 있는 항목이다.**

### B-2. `ai_invocations.is_token_estimated` 추가

`docs/api-contracts/admin.md`에서 "'추정' 플래그에 대응하는 소스 컬럼이 없음"으로 표시했던 항목이 해소된다.
관리자 비용 화면이 추정값과 실측값을 구분해 표시할 수 있다.

### B-3. `retention_policies.target_entity`에 `INVOCATIONS` 추가

`admin.md`의 `llm_calls` ENUM 누락 지적이 해소된다. 프론트 라벨 매핑만 맞추면 된다.

### B-4~B-6

- `ai_invocations.status`에 `TIMEOUT`, `RATE_LIMITED` 추가 — 실패 원인 구분 가능
- `ai_invocations.is_fallback` 추가 — 대체 모델 처리 추적
- `article_id` FK 7개 복구 — 애플리케이션이 지던 참조 무결성 책임을 DB로 되돌림

---

## 4. C — 결정이 필요한 변경

### C-1. 다중 프로바이더 전환은 스키마 변경이 아니라 **스택 변경**이다 · 담당 **B**

`model_id` 단일 컬럼을 `provider` + `model_name`으로 분리하고, 헤더에서 Bedrock 표현을 전부 제거했다.
영향 범위가 스키마 밖이다:

| 문서 | 현재 내용 |
|---|---|
| 루트 `CLAUDE.md` §2 | 기술 스택 표 `AI \| Amazon Bedrock (요약/번역)` |
| §1 | 핵심 제약 문장 자체가 "조회 시점에 **Bedrock**을 호출하지 않는다" |
| §3 | B 담당 정의 "**Bedrock** 요약 생성(한 줄/3줄/상세)" |
| §8 미결 | "**Bedrock** 모델 ID 고정 방식 — `summaries.model_id`에 실제 사용값을 기록" |
| §9 | "**Bedrock** 호출은 `modules/ai/services` 밖에서 하지 않는다" |

**프론트 정합성 측면에서는 오히려 유리하다.** 프로토타입과 현재 구현이 이미 다중 프로바이더를 전제로 한다:

- `frontend/src/types/admin.ts` — `PipelineRun.provider: string`, `ModelUsage.provider: string`
- `frontend/src/constants/theme.ts` — `colors.provider = { openai, claude, gemini, other }`
- `frontend/src/pages/admin/LLMUsagePage.tsx` — 3개 프로바이더를 색 + 선 패턴으로 구분해 차트에 표시
- `frontend/src/mocks/llmUsageMockData.ts` — `claude-sonnet-5` / `gpt-4o` / `gemini-2.0-flash`

`admin.md`에 "provider 개념이 스키마에 없고 Bedrock 단일 스택과 충돌한다"고 남긴 항목이 이 변경으로 해소된다.
**다만 이건 D가 단독으로 확정할 사안이 아니다.** B 모듈 정의 전체가 바뀌므로 B의 판단이 필요하고,
확정되면 루트 `CLAUDE.md` §1·§2·§3·§8·§9와 `.claude/skills/ai-module/SKILL.md`를 함께 고쳐야 한다.

> 참고: "조회 시점에 LLM을 호출하지 않는다"는 핵심 제약은 프로바이더가 몇 개든 그대로 유효하다.
> 오히려 프로바이더가 늘면 비용 추적의 중요도가 올라간다.

### C-2. 파티셔닝 제거 — §8 미결 사항을 FK 쪽으로 확정 · 담당 **C**

루트 `CLAUDE.md` §8 미결 사항:

> **`articles` 파티셔닝 vs FK** — `published_at` 월 단위 파티셔닝은 보관 정책을 `DROP PARTITION`으로
> 즉시 처리할 수 있지만, MySQL 제약상 파티셔닝 테이블은 FK 대상이 될 수 없어 `article_id` 무결성을
> 애플리케이션이 책임져야 한다. 일 수천 건 규모라면 파티셔닝을 빼고 FK를 살리는 쪽이 운영이 단순하다.
> (C 담당, 예상 기사량 확정 후 결정)

제안 파일은 FK를 택했다. 근거("일 수천 건이면 `BATCH_DELETE`로 충분")가 루트 문서가 이미 기울어 있던
방향과 같으므로 **판단 자체는 타당하다.** B-1(유니크 정상화)이 이 결정의 부수 효과로 따라온다는 점도 근거를 강화한다.
결정 주체가 C이므로 확인만 필요하다.

### C-3. `cost_budgets`에 유니크 제약이 **새로 추가**됐다 · 담당 **B**

```sql
UNIQUE KEY uk_budgets_period (period_type) COMMENT '기간 유형별 예산은 하나만 유지'
```

V1.1에 없던 업무 규칙이다. `DAILY`/`MONTHLY` 각 1행만 허용되므로 프로바이더별 예산이나
알림 채널별 예산을 만들 수 없다. **C-1(다중 프로바이더)과 방향이 서로 어긋난다** —
프로바이더가 여러 개가 되면 "OpenAI 일일 한도"와 "Anthropic 일일 한도"를 따로 두고 싶어질 가능성이 높다.

선택지:
- **(a)** 유니크를 뺀다 — 예산 행을 여러 개 허용, 애플리케이션이 중복 정책을 판단
- **(b)** `UNIQUE (period_type, provider)`로 확장 — `provider` 컬럼 추가 필요, `NULL`을 "전체"로 쓰면
  MySQL 유니크는 `NULL`을 중복 허용하므로 전체 예산의 유일성은 보장되지 않는다
- **(c)** 그대로 둔다 — 초기에는 전체 한도 하나로 충분하다고 보고 나중에 확장

---

## 5. D — 신규 파일의 결함

### D-1. `articles` 삭제 시 요약·번역 연쇄 삭제 → **RESTRICT로 반영 완료** ✅

제안 파일의 최초 버전은 FK를 복구하면서 다음과 같이 CASCADE를 걸었다:

```
articles ──CASCADE──> summaries ──CASCADE──> translations
         └─CASCADE──> feed_items
```

`retention_policies(target_entity='ARTICLES', strategy='BATCH_DELETE')` 배치가 도는 순간
**비용을 들여 만든 요약·번역이 연쇄 삭제된다.** 원문은 URL로 재수집할 수 있지만 요약은 LLM을 다시
호출해야 만들어진다. 루트 `CLAUDE.md` §1의 "요약·번역은 배치에서만 생성해 MySQL에 **영구 저장**"과
정면으로 충돌하며, 이 프로젝트 기준으로는 성능 문제가 아니라 **비용 사고**다.

V1.1은 파티셔닝 탓에 FK가 아예 없어 이 사고가 구조적으로 불가능했다. FK 복구와 함께 새로 생긴 위험이다.

**반영 내용** — `fk_summaries_article`과 `fk_feed_article`을 `ON DELETE RESTRICT`로 변경했다.
요약이 남아 있는 원문은 삭제 자체가 실패한다.

**C(retention.py 담당)에게 미치는 영향**: `ARTICLES` 정책을 다음 중 하나로 구현해야 한다.

- **(a) soft purge (권장)** — `articles.content`를 `NULL`로만 만들고 행은 남긴다.
  저장공간(LONGTEXT)은 회수되고 요약은 보존된다. 다만 정책의 `strategy` 값 의미가 "행 삭제"가 아니게 되므로
  `retention_policies`에 별도 표현이 필요할 수 있다.
- **(b) hard delete** — `DELETE summaries`(→ `translations`, `feed_items` CASCADE) → `DELETE articles`
  순서로, "요약을 버린다"는 판단을 명시적으로 먼저 내린다.

### D-2. `retention_policies.strategy`의 `PARTITION_DROP`이 남아 있다 · 담당 **C**

파티셔닝을 제거했으므로 실행 불가능한 값이다. 관리자 화면에서는 선택 가능하고 배치는 실패한다.
ENUM에서 제거할지, 향후 파티셔닝 재도입 여지로 남길지 정해야 한다.
남긴다면 프론트에서 선택지로 노출하지 않도록 `admin.md` 계약에 명시가 필요하다.

### D-3. 배치 실행기 비결합 원칙이 헤더에서 사라졌다 · 담당 **전원**

V1.1 헤더에는 있었고 제안 파일에서 빠진 문장:

> 배치 실행 기술(스케줄러/큐)은 미정 — 스키마는 특정 실행기에 결합하지 않는다.

`task_ref` 컬럼 주석에서도 "기술 미정"이 빠졌다. 대신 헤더에 `LangChain`이라는 특정 라이브러리명이 들어왔다.
§8.2는 이 원칙을 확정 사항으로 두고 있고, `celery_task_id` → `task_ref` 개명의 근거였다.
같은 기준을 적용하면 LangChain도 헤더에 박지 않고 `provider`/`model_name` 컬럼 주석 수준으로 두는 편이 일관적이다.

### D-4. Redis 주석 라인 삭제 (사소)

"(배치 브로커 용도는 실행 기술 확정 후 추가)" 삭제 — §8 미결 사항 리마인더가 사라졌다.

---

## 결정 필요 안건

| # | 안건 | 담당 | 비고 |
|---|---|---|---|
| C-1 | 다중 프로바이더 전환 확정 여부 | **B** | 확정 시 루트 `CLAUDE.md` §1·§2·§3·§8·§9 개정 필요 |
| C-2 | 파티셔닝 제거 + FK 유지 확정 | **C** | §8 미결 사항 해소. B-1이 부수 효과로 따라옴 |
| C-3 | `cost_budgets` 기간별 유니크 유지 여부 | **B** | C-1과 방향 충돌 |
| D-2 | `PARTITION_DROP` ENUM 값 처리 | **C** | 남기면 `admin.md`에 노출 금지 명시 |
| D-3 | 헤더의 특정 기술명 표기 방침 | 전원 | §8.2 원칙과의 정합성 |
| — | `ARTICLES` 보관 정책 구현 방식 (soft purge vs hard delete) | **C** | D-1의 후속. `retention.py` 설계에 직결 |
| — | 인덱스 추가 시점 | **C** | 시연 전 `idx_feed_list`만이라도 넣을지 |

합의 후 처리 순서:
1. C-1 확정 → 루트 `CLAUDE.md` 및 `.claude/skills/ai-module/SKILL.md` 개정 (B, 별도 PR)
2. C-2·C-3·D-2·D-3 확정 → `schema.sql`을 V2로 갱신 (**C**)
3. C가 Alembic revision 생성 → 머지 후 각자 rebase (§5 규칙 6)
4. `docs/db/ERD.md`, `docs/api-contracts/admin.md` 후속 갱신

---

## 프론트 후속 작업 (D, 이 PR 범위 밖)

C-1이 확정되면:

- `frontend/src/types/admin.ts` — `provider: string`을 스키마 값(`openai`/`anthropic`/`google`)에 맞춘 유니온으로 좁힌다.
  현재 목업은 표시용 라벨(`'Claude'`, `'OpenAI'`, `'Gemini'`)을 쓰고 있어 라벨 매핑이 필요하다.
- `theme.ts`의 `colors.provider` 키(`openai`/`claude`/`gemini`/`other`)를 스키마 `provider` 값과 맞춘다
  (`claude` → `anthropic`, `gemini` → `google`). **디자인 값 변경이 아니라 키 이름 변경이다.**
- `is_token_estimated`, `is_fallback`을 화면에 노출할지 결정하고 `admin.md`에 반영한다.
- `retention_policies`에 `INVOCATIONS`가 추가되면 RetentionPage에 항목 1개가 늘어난다.
