# CLAUDE.md

> 이 파일은 Claude Code(및 이 리포지토리에서 작업하는 모든 Claude 인스턴스)가 **가장 먼저 읽어야 하는 프로젝트 규칙 문서**다.
> 모듈별 세부 규칙은 `.claude/skills/*/SKILL.md` 를 참고하되, 여기 적힌 전역 규칙이 항상 우선한다.

---

## 1. 프로젝트 개요

**NewsBrief** — AI 뉴스 요약·번역 개인화 피드 서비스.

- 수집: 외부 News API에서 기사(제목/본문/URL/발행일)를 하루 3회(07:00 / 12:00 / 17:00) 배치 수집, URL 기준 중복 제거
- 요약/번역: Bedrock 모델로 기사 요약(한 줄/3줄/상세) 후 사용자 지정 언어로 번역
- 배포: 사용자 관심 태그에 매칭되는 기사만 선별해 개인화 피드로 제공
- 운영: 파이프라인 처리 현황·오류 확인, Bedrock 호출량/비용 추적 및 임계치 알림, 데이터 보관 정책

**설계의 핵심 제약 — 조회 시점에 Bedrock을 호출하지 않는다.**
요약·번역은 배치에서만 생성해 MySQL에 영구 저장하고, 사용자 요청은 저장된 결과 조회로만 응답한다. 이 원칙을 깨는 구현(요청 시 실시간 요약, 캐시 미스 시 온디맨드 호출 등)은 성능이 아니라 **비용 사고**로 취급한다.

기준 문서: `docs/requirements.xlsx`(요구사항 명세서), `docs/db/schema.sql`(DDL), `docs/db/ERD.md`(도메인별 ERD).

## 2. 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React + TypeScript (Vite) |
| Backend | FastAPI (Python) |
| DB | MySQL 8.0 (utf8mb4) |
| 세션/캐시 | Redis (로그인 세션, 피드 캐시) |
| 배치 | **미정** — 스케줄러/큐 기술 선정 전 (§8 미결 사항 참고) |
| AI | Amazon Bedrock (요약/번역) |
| IaC | Terraform (`infra/` 공간만 확보, 작성 시점 미정) |
| 형상관리 | Git (GitHub) |

**배치 기술이 미정이므로 배치 로직은 실행기에 결합시키지 않는다.** 수집·요약·번역·큐레이션 로직은 `backend/app/batch/*.py`에 **인자를 받아 결과를 반환하는 순수 함수/서비스 호출** 형태로 작성하고, 스케줄 트리거(데코레이터, 브로커 설정, 워커 엔트리포인트)는 기술 확정 후 별도 계층에서 붙인다. 특정 라이브러리 데코레이터를 함수에 직접 붙이는 구현은 금지.

## 3. 팀 구성 및 모듈 소유권 (Ownership Map)

브랜치 충돌을 막기 위해 **디렉토리 경계 = 담당자 경계**로 설계했다. 레이어(프론트/백)로 일괄 분할하지 않고 **파이프라인 단계로 수직 분할**한 이유는, 이 프로젝트가 수집 → 요약 → 번역 → 피드의 순차 의존 구조여서 레이어로 자르면 대기와 충돌이 동시에 발생하기 때문이다. 단, 유일한 화면 영역인 사용자/관리자 프론트엔드는 분량이 1인 몫이 되므로 D가 전담한다.

각자 자신의 모듈 디렉토리 밖의 파일은 원칙적으로 수정하지 않는다 (공용 파일 수정 규칙은 §5 참고).

| 담당 | 모듈 코드 | 담당 기능 | 소유 디렉토리 |
|---|---|---|---|
| **A** | `collector` | 뉴스 API 연동, 수집 스케줄 대상 정의, 키워드/카테고리/언론사 필터링, 중복 기사 제거, 수집 오류·재시도, 파이프라인 처리 현황 집계 API | `backend/app/modules/collector/*`, `backend/app/batch/collect.py` |
| **B** | `ai` | Bedrock 요약 생성(한 줄/3줄/상세), 다국어 번역, 요약 검수 플래그, 요약/번역 결과 영구 저장, 호출량·비용 기록 및 임계치 알림 | `backend/app/modules/ai/*`, `backend/app/batch/{summarize,translate}.py` |
| **C** | `feed` (Backend) | 회원가입/로그인(Redis 세션), 관심 태그 등록·관리, 콘텐츠 큐레이션 배치, 뉴스 피드 조회 API, 원문 링크 제공, 데이터 보관 정책 배치 | `backend/app/modules/{auth,feed}/*`, `backend/app/batch/{curate,retention}.py`, `backend/app/db/migrations` |
| **D** | `web` (Frontend) | React 앱 전체 — 로그인/회원가입, 마이페이지, 관심 태그 설정, 피드 목록/상세, 북마크, 관리자 모니터링·비용 대시보드 | `frontend/src/**` (아래 공용 영역 제외) |
| 공용(합의 필요) | `_shared` | 공용 컴포넌트/라우팅/디자인 토큰, DB 세션, 공통 예외/로깅, 배치 엔트리포인트, Terraform | `backend/app/{core,db,common}`, `backend/app/main.py`, `frontend/src/{routes,constants}`, `frontend/src/components/common`, `frontend/src/api/client.ts`, `frontend/src/types/common`, `infra/`, `.github/workflows/` |

### 프론트/백 경계 운영 (C ↔ D)

C�� D는 같은 기능을 양쪽에서 나눠 갖기 때문에 **API 계약이 곧 인터페이스**다.

- 화면 하나당 계약을 먼저 확정한다: `docs/api-contracts/feed.md`, `auth.md`, `admin.md`
- 계약 PR은 **C·D 두 명이 모두 승인**해야 머지된다. 계약 없이 시작한 구현은 반려.
- D는 계약 기준 mock으로 화면을 먼저 만들고, C의 API가 붙으면 mock을 제거한다.
- 응답 필드명·null 규칙·페이지네이션 방식은 계약 문서가 유일한 기준이며, 구현이 다르면 계약이 아니라 코드를 고친다.
- 관리자 대시보드가 쓰는 집계 API는 A(파이프라인 현황)와 B(비용/사용량)가 각각 제공한다. D는 화면만 담당하되 필요한 응답 형태를 계약으로 먼저 요청한다.

### 테스트

**통합 이후 각 담당이 자신의 모듈을 각자 테스트한다.** 별도 QA 담당을 두지 않는다.

- 각자 자기 모듈 디렉토리 하위에 `tests/`를 두고 최소 정상 경로 1개 + 실패 경로 1개를 유지한다.
- 남의 모듈 테스트를 수정하지 않는다. 남의 모듈 때문에 자기 테스트가 깨지면 이슈로 등록한다.
- 배치 로직은 실행기 없이 함수 단위로 테스트 가능해야 한다 (§2 참고).
- CI는 전체 테스트를 실행하되, 실패한 테스트의 수정 책임은 해당 모듈 소유자에게 있다.

### Alembic / 인프라 창구

- **DB 마이그레이션 창구는 C다.** `backend/app/db/migrations`는 C가 소유하며, 스키마 변경이 필요하면 이슈 등록 후 C가 revision을 생성한다 (이유는 §5 충돌 방지 규칙 6번).
- `infra/`(Terraform)와 `.github/workflows/`는 소유자를 고정하지 않는다. 디렉토리와 최소 스켈레톤만 확보해 두고, 작성 시점·담당은 팀에서 별도 합의한다.

## 4. 디렉토리 구조

```
newsbrief/
├── CLAUDE.md                      # 이 파일
├── .claude/skills/                # Claude Code용 모듈별 스킬 (아래 §6)
├── docs/                          # 요구사항 명세서, ERD, DB 스키마, API 계약
│   ├── db/{schema.sql, ERD.md, seed.sql}
│   └── api-contracts/{collector,ai,feed,auth,admin}.md
├── frontend/                      # React 웹 앱 (D 소유)
│   └── src/{app,routes,pages,components,store,api,types,hooks,constants,utils}/
│       └── (auth | feed | admin | common) 하위 분리
├── backend/                       # FastAPI 서버
│   └── app/
│       ├── {core,db,common}/       # 설정, 세션, 공통 예외/로깅 (공용)
│       ├── batch/                  # 배치 로직 (파일 단위로 소유자 분리, 실행기 비의존)
│       └── modules/(collector | ai | auth | feed)/
│           └── {routers,schemas,services,models}
├── infra/                         # Terraform 공간 (담당·시점 미정)
└── .github/workflows/             # CI
```

전체 디렉토리 트리는 `docs/DIRECTORY_STRUCTURE.md` 참고.

## 5. Git 협업 규칙

### 브랜치 전략
- `main`: 배포 가능 상태만 유지, 직접 push 금지 (브랜치 보호 설정)
- `develop`: 통합 브랜치. 머지 조건은 **리뷰 1인 승인 + CI 통과**
- 기능 브랜치: `feature/{module}/{task}` 예) `feature/collector/news-api-client`, `feature/web/tag-settings-page`
- 수정 브랜치: `fix/{module}/{issue}`

### 커밋 컨벤션 (Conventional Commits)
```
<type>(<module>): <description>

type: feat | fix | refactor | style | docs | test | chore
module: collector | ai | auth | feed | web | shared | infra
```
예) `feat(collector): URL 해시 기반 중복 기사 필터 추가`

### 충돌 방지 규칙
1. **자기 모듈 디렉토리 밖은 건드리지 않는다.** 공용 영역(`components/common`, `routes`, `core`, `db`, `common`)이 필요하면 직접 고치지 말고 이슈로 등록 후 담당 합의.
2. **공용 파일을 고쳐야 하는 경우**(`main.py`, `routes/*`, `client.ts`, 배치 엔트리포인트) → 반드시 별도 PR로 분리하고 전원 리뷰 필수.
3. 타입/스키마는 모듈별 `types/{module}` 또는 모듈 `schemas/`에만 선언하고, 다른 모듈이 참조해야 하면 `types/common`으로 승격 후 사용 (다른 모듈 폴더에서 직접 import 금지).
4. API 계약은 코드 작성 전 `docs/api-contracts/{module}.md`에 먼저 정의하고 PR로 리뷰받는다. C·D 사이의 계약은 양측 승인 필수.
5. **배치 로직은 파일 단위로 소유권을 나눈다.** 한 파일에 여러 담당의 배치를 섞지 않는다 (`collect.py`=A, `summarize.py`/`translate.py`=B, `curate.py`/`retention.py`=C).
6. **DB 스키마 변경은 C를 창구로 단일화한다.** 두 명이 각자 브랜치에서 Alembic revision을 만들면 head가 갈라져 머지 후 마이그레이션이 깨진다. 변경 필요 시 이슈 등록 → C가 revision 생성 → 머지 후 각자 rebase. 기존 마이그레이션 파일 직접 수정은 금지.
7. `requirements.txt` / `package.json`은 한 줄 추가도 자주 겹친다. 추가한 PR은 rebase 후 즉시 머지한다.

### PR 규칙
- PR 제목에 모듈 태그 포함: `[collector] 뉴스 API 클라이언트 구현`
- 본인 모듈 범위를 벗어난 변경이 diff에 섞여 있으면 반려
- 머지 전 최소 1인 리뷰 (공용 파일 변경 시 전원 리뷰)
- PR 단위는 300줄 이하를 목표로 한다. 배치 로직은 커밋이 뭉치기 쉬우므로 "기능 1개 = PR 1개"를 의식적으로 지킨다.
- 이슈 제목은 **요구사항 명세서의 기능명을 그대로** 사용해 추적성을 유지한다. 라벨은 담당 영역(`collector`/`ai`/`feed`/`web`) + 중요도(`P-상`/`P-중`/`P-하`)만.
- `CODEOWNERS`에 §3 표의 디렉토리를 등록해 리뷰어를 자동 배정한다.

### 의존 순서와 병렬화
A → B → C → D는 데이터 의존이지만 **그대로 기다리면 4명이 직렬화된다.** 다음을 전제로 병렬 작업한다.

- 0주차에 넷이 함께: 리포 구조, FastAPI 스켈레톤, `docker-compose.yml`(MySQL·Redis·API), 초기 마이그레이션(C가 스키마 전체를 한 번에 커밋), `.env.example`, 린트·포맷 설정, CI 워크플로, `docs/api-contracts/` 초안.
- B는 A의 실제 수집 데이터 대신 `docs/db/seed.sql`의 시드 기사로 개발을 시작한다.
- C는 시드 요약·번역 데이터로 큐레이션과 피드 API를 먼저 만든다.
- D는 계약 기반 mock 응답으로 화면 전체를 먼저 만든다. **D는 계약이 확정되기 전에는 아무것도 시작할 수 없으므로, 계약 문서 작성이 0주차의 최우선 과제다.**
- 통합 순서: A+B(수집~요약 배치) → +C(피드 API) → +D(화면 연결).

## 6. Claude Code 스킬 (.claude/skills)

모듈별 세부 작업 규칙(파일 위치, API 엔드포인트 네이밍, DB 테이블, 하지 말아야 할 것)은 스킬 파일에 있다. **해당 모듈 작업 시 반드시 먼저 로드한다.**

| 스킬 | 위치 | 담당 |
|---|---|---|
| collector-module | `.claude/skills/collector-module/SKILL.md` | A |
| ai-module | `.claude/skills/ai-module/SKILL.md` | B |
| feed-module | `.claude/skills/feed-module/SKILL.md` | C |
| web-module | `.claude/skills/web-module/SKILL.md` | D |
| _shared | `.claude/skills/_shared/SKILL.md` | 공용 컨벤션/디자인 토큰/공통 컴포넌트 규칙 |

## 7. 코딩 컨벤션 요약

- **Frontend**: 함수형 컴포넌트 + TypeScript, 페이지 컴포넌트명은 `XxxPage`, 색상/폰트는 `frontend/src/constants/theme.ts`의 디자인 토큰만 사용. 서버 상태는 TanStack Query, 클라이언트 상태만 store에 둔다. API 호출은 반드시 `api/{module}` 레이어를 경유하고 컴포넌트에서 직접 `fetch`하지 않는다.
- **Backend**: 모듈 = `routers`(엔드포인트) / `schemas`(Pydantic) / `services`(비즈니스 로직) / `models`(SQLAlchemy) 4단 구조 고정. **라우터에 비즈니스 로직 작성 금지. Bedrock 호출은 `modules/ai/services` 밖에서 하지 않는다.**
- **SQLAlchemy 모델은 도메인별 파일로 분리한다** (`models/article.py`, `models/user.py` …). 단일 `models.py`는 충돌의 온상이므로 만들지 않는다.
- **배치는 실행기 비의존으로 작성한다** (§2). 스케줄 관련 상수(실행 시각 등)는 설정으로 외부화한다.
- **네이밍**: 프론트 폴더는 kebab-case, 백엔드 파이썬 모듈은 snake_case — 언어 컨벤션에 맞춰 의도적으로 다르게 유지. DB 테이블/컬럼은 snake_case, 테이블명은 복수형.
- **시크릿**: API 키·DB 접속정보를 코드/설정 파일에 절대 하드코딩하지 않는다. 로컬은 `.env`(gitignore), 배포는 시크릿 관리 도구. `.env.example`만 커밋한다.
- **로깅**: 배치 처리 결과는 print가 아니라 `batch_jobs` / `job_logs` 테이블에 기록한다 (요구사항: 수집 오류 처리).
- **디자인 토큰** (전 모듈 공통, 임의 색상 사용 금지):
  - 프라이머리 딥네이비 `#1F3A5F` / 배경(밝음) `#FAFAF8` / 서페이스(톤다운) `#EFEDE7` / 강조 `#C2410C` / 상태색: 성공 `green-600`, 경고 `amber-600`, 오류 `red-600`

## 8. 확정된 결정 사항 (스키마 V1.1) / 남은 미결 사항

`docs/db/schema.sql` 초안 검토 중 확정된 사항이다. 스키마는 **V1.1**로 갱신했고, 각 모듈 SKILL.md도 반영했다.

1. **`article_chunks` 테이블을 제거했다.** 요구사항 "긴 기사 청크 분할"이 스코프에서 빠졌으므로, 분할 저장 테이블과 `summaries.chunk_count` 컬럼을 모두 삭제한다. (~~V1 초안의 청크 분할·병합 요약 설계는 이 문서로 대체된다~~ — B 담당은 청크 병합 로직을 구현하지 않는다)
2. **배치 실행 기술은 미정이며, 스키마도 특정 기술에 결합시키지 않는다.** `batch_jobs.celery_task_id`는 `batch_jobs.task_ref`(실행기 식별자, 기술 중립)로 변경했다. Redis 키 설계에서도 브로커 용도는 제외하고 세션/캐시/락만 남긴다.
3. **중복 제거는 이중 방어로 확정.** Redis `dedup:url:{yyyymmdd}` SET으로 INSERT 전 1차 필터링하되, 최종 보증은 `articles.url_hash`(정규화 URL의 SHA-256) 유니크 인덱스가 담당한다. Redis만 믿는 구현 금지. (A 담당)
4. **재호출 방지 유니크 키 확정.** `summaries`는 `(article_id, summary_type)`, `translations`는 `(summary_id, target_language)` 유니크. 같은 조합이 두 번 생성되면 곧 비용 중복이므로 UPSERT로 처리한다. (B 담당)
5. **`feed_items` INSERT는 C가 소유한다.** B는 `summaries` / `translations`까지만 쓰고, 피드 행 생성은 C의 `curate.py` 배치가 담당한다. 이 경계를 넘는 PR은 반려한다.
6. **Redis는 세션/캐시 전용.** 요약·번역 본문을 Redis에만 두는 구현 금지 (영구 저장은 MySQL). Redis 키 설계는 `docs/db/schema.sql` 하단 주석 참고.
7. **테스트는 통합 이후 각 담당이 자기 모듈을 각자 수행한다.** 전담 QA/인프라 담당을 두지 않는다. (§3 테스트 항목)
8. **Terraform은 공간만 확보한다.** `infra/` 디렉토리와 스켈레톤만 두고, 작성 담당·시점은 별도 합의로 미룬다.

### 남은 미결 사항
- **배치 실행 기술 선정** — 스케줄러/큐를 무엇으로 할지 미정. 하루 3회 고정 배치라는 요구사항만 확정. 선정 전까지 §2 규칙(실행기 비의존)을 지킨다. (전원 합의 사항)
- **요약 3종 저장 여부** — 현재 스키마는 한 줄/3줄/상세를 별도 row로 두지만, 배치에서 세 종류를 다 만들면 Bedrock 호출이 3배가 된다. "상세 1건만 저장 + 짧은 버전은 프런트에서 절단" 안과 비교 검토 필요. (B·D 협의, 비용 추정 후 결정)
- **`articles` 파티셔닝 vs FK** — `published_at` 월 단위 파티셔닝은 보관 정책을 `DROP PARTITION`으로 즉시 처리할 수 있지만, MySQL 제약상 파티셔닝 테이블은 FK 대상이 될 수 없어 `article_id` 무결성을 애플리케이션이 책임져야 한다. 일 수천 건 규모라면 파티셔닝을 빼고 FK를 살리는 쪽이 운영이 단순하다. (C 담당, 예상 기사량 확정 후 결정)
- **토큰 제한 초과 기사 처리** — 청크 분할을 하지 않기로 했으므로 대안을 정해야 한다. (a) `articles.status='FAILED'` + `job_logs.error_code='TOKEN_LIMIT_EXCEEDED'`로 스킵, (b) 본문 앞부분만 잘라 요약하고 `summaries.is_truncated` 플래그 추가. (b)를 택하면 스키마 변경이 필요하다. (B 담당)
- **번역 지원 언어 목록** — `users.preferred_language`와 `translations.target_language`의 허용 값 확정 필요. 지원 언어가 늘어날수록 호출 비용이 선형 증가하므로 초기에는 최소 집합으로 시작. (B·C 협의)
- **Bedrock 모델 ID 고정 방식** — 모델 ID를 환경변수로 주입하고 `summaries.model_id`에 실제 사용값을 기록한다는 원칙만 확정. 어떤 모델을 기본값으로 쓸지는 미결. (B 담당)
- **비용/실패 알림 채널** — `cost_budgets.notify_channel`의 실제 전송 수단과 배치 실패 알림 경로 미정. (B 담당)
- **Terraform·CI/CD 담당과 착수 시점** — 미정. (전원 합의 사항)

## 9. Claude에게 주는 전역 지시사항

- 항상 **§3 소유권 표에 명시된 디렉토리 범위 안에서만** 파일을 생성/수정한다. 범위를 벗어나야 하는 작업이면 먼저 사용자에게 알린다.
- **조회 경로에 Bedrock 호출을 넣지 않는다.** 피드/상세 조회 API를 구현할 때 요약이 없으면 생성하는 코드를 절대 쓰지 말고, 저장된 결과가 없으면 해당 기사를 응답에서 제외하거나 명시적 상태값으로 반환한다.
- **배치 실행 기술을 임의로 선택하지 않는다.** 특정 스케줄러/큐 라이브러리를 설치하거나 데코레이터·설정 파일을 추가하지 말고, 실행기에 의존하지 않는 함수로 작성한 뒤 트리거가 필요하면 사용자에게 알린다.
- **스키마 변경이 필요한 작업**이면 코드를 먼저 쓰지 않고, 변경 내용을 정리해 사용자에게 알린 뒤 C 창구를 통하도록 안내한다. Alembic revision을 임의 생성하지 않는다.
- 새 API를 만들 때는 먼저 `docs/api-contracts/{module}.md`에 계약이 있는지 확인하고, 없으면 만들어 사용자 확인을 받은 뒤 구현한다. 프론트 작업 시 계약에 없는 응답 필드를 가정하지 않는다.
- API 키·DB 접속정보 등 시크릿을 코드나 커밋에 포함하지 않는다. 예시가 필요하면 `.env.example`에 플레이스홀더로만 쓴다.
- 배치를 구현할 때는 실행 이력(`batch_jobs`)과 오류(`job_logs`) 기록, Bedrock 호출 시 `ai_invocations` 기록을 항상 함께 남긴다.
- 모듈 코드를 작성하면 같은 모듈 `tests/`에 최소 테스트를 함께 추가한다 (§3 테스트).
- 커밋 메시지는 §5 컨벤션을 따른다.
