# CLAUDE.md

> 이 파일은 Claude Code(및 이 리포지토리에서 작업하는 모든 Claude 인스턴스)가 **가장 먼저 읽어야 하는 프로젝트 규칙 문서**다.
> 모듈별 세부 규칙은 `.claude/skills/*/SKILL.md` 를 참고하되, 여기 적힌 전역 규칙이 항상 우선한다.

---

## 1. 프로젝트 개요

**NewsBrief** — AI 뉴스 요약·번역 개인화 피드 서비스.

- 수집: 외부 News API에서 기사(제목/본문/URL/발행일)를 하루 3회(07:00 / 12:00 / 17:00) 배치 수집, URL 기준 중복 제거
- 요약/번역: LLM으로 기사 요약(한 줄/3줄/상세) 후 사용자 지정 언어로 번역
- 배포: 사용자 관심 태그에 매칭되는 기사만 선별해 개인화 피드로 제공
- 운영: 파이프라인 처리 현황·오류 확인, LLM 호출량/비용 추적 및 임계치 알림, 데이터 보관 정책

**설계의 핵심 제약 — 조회 시점에 LLM을 호출하지 않는다.**
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
| AI | LLM 다중 프로바이더 (요약/번역). 프로바이더·모델은 환경변수로 주입하고 실제 사용값을 `summaries.provider` / `model_name`에 기록한다 — 스키마·코드에 특정 프로바이더나 클라이언트 라이브러리를 박지 않는다 |
| IaC | Terraform (`infra/` 공간만 확보, 작성 시점 미정) |
| 형상관리 | Git (GitHub) |

### 2.1 로컬 개발·테스트 환경

**Docker를 쓰지 않는다.** 각자 로컬에 설치한 MySQL·Redis에 직접 붙는다. 컨테이너 오케스트레이션을
얹을 만큼 구성이 복잡하지 않고, 팀원마다 이미 로컬 MySQL이 떠 있다.

접속 정보는 `backend/.env`(gitignore)에 두고, 커밋되는 것은 `backend/.env.example`의 플레이스홀더뿐이다.

```
DATABASE_URL=mysql+pymysql://<user>:<pw>@127.0.0.1:3306/news_ai?charset=utf8mb4
REDIS_URL=redis://localhost:6379/0
SESSION_COOKIE_SECURE=false   # 로컬 http에서 브라우저가 쿠키를 저장하게 하려면 필요
```

스키마는 **Alembic으로만** 만든다. `schema.sql`을 손으로 실행하지 않는다 — 두 경로가 갈리면
어느 쪽이 진실인지 알 수 없게 된다.

```bash
cd backend
mysql -u <user> -p -e "CREATE DATABASE IF NOT EXISTS news_ai \
  DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_0900_ai_ci"
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed_dev.py    # 로컬 개발용 시드 (운영 DB에 절대 실행 금지)
```

#### 실행

```bash
# 터미널 1 — 백엔드
cd backend && .venv/bin/uvicorn app.main:app --reload    # http://localhost:8000/docs

# 터미널 2 — 프론트
cd frontend && npm run dev                               # http://localhost:5173
```

프론트는 `/api` 요청을 Vite 프록시로 백엔드에 넘긴다(`vite.config.ts`, 기본 `127.0.0.1:8000`).
MSW 목업은 기본으로 꺼져 있다 — `VITE_USE_MSW=true`일 때만 뜬다. 켜져 있으면 실제 API 응답을
가로채므로 백엔드 연동 확인이 불가능해진다.

> **주의 — 환경변수가 `.env`를 이긴다.** 셸에 `DATABASE_URL`이 export 돼 있으면 `.env`에 뭘 적어도
> 그 값이 쓰인다. "분명 MySQL로 바꿨는데 SQLite 데이터가 나온다" 싶으면 `env | grep DATABASE_URL`
> 부터 확인하고, `.env`를 쓰려면 그 변수를 지운 새 셸에서 실행한다. 응답의 `publishedAt`에
> 마이크로초가 붙어 있으면(`...T05:24:40.368981`) SQLite다 — MySQL `DATETIME`은 초까지만 저장한다.

#### 테스트는 두 모드로 돌린다

| 모드 | 명령 | 언제 |
|---|---|---|
| SQLite (기본) | `.venv/bin/python -m pytest app` | 평소. 외부 의존 없이 빠르다 |
| **로컬 MySQL** | `TEST_DATABASE_URL=... .venv/bin/python -m pytest app` | **모델·스키마·마이그레이션을 건드린 뒤** |

```bash
# 테스트 전용 스키마를 Alembic으로 올린다 (최초 1회, 스키마가 바뀌면 다시)
mysql -u <user> -p -e "CREATE DATABASE IF NOT EXISTS news_ai_test \
  DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_0900_ai_ci"
DATABASE_URL="mysql+pymysql://<user>:<pw>@127.0.0.1:3306/news_ai_test?charset=utf8mb4" \
  .venv/bin/alembic upgrade head

TEST_DATABASE_URL="mysql+pymysql://<user>:<pw>@127.0.0.1:3306/news_ai_test?charset=utf8mb4" \
  .venv/bin/python -m pytest app
```

**MySQL 모드가 왜 필요한가.** SQLite 모드는 SQLAlchemy 모델로 테이블을 만든다(`create_all`).
그래서 **모델이 실제 스키마와 어긋나도 테스트가 통과한다** — 어긋난 모델대로 테이블이 생기기 때문이다.
실제로 `read_only.py`가 `NOT NULL` 컬럼 5개(`articles.url_hash` 포함)를 빠뜨린 채 SQLite 테스트를
전부 통과했고, 진짜 스키마에 붙이자마자 INSERT가 깨졌다. MySQL 모드는 **테이블을 만들지 않고
Alembic이 올린 스키마에 그대로 붙으므로** 이 부류를 잡는다. 구현은 `backend/app/db/testing.py`.

**배치 기술이 미정이므로 배치 로직은 실행기에 결합시키지 않는다.** 수집·요약·번역·큐레이션 로직은 `backend/app/batch/*.py`에 **인자를 받아 결과를 반환하는 순수 함수/서비스 호출** 형태로 작성하고, 스케줄 트리거(데코레이터, 브로커 설정, 워커 엔트리포인트)는 기술 확정 후 별도 계층에서 붙인다. 특정 라이브러리 데코레이터를 함수에 직접 붙이는 구현은 금지.

## 3. 팀 구성 및 모듈 소유권 (Ownership Map)

브랜치 충돌을 막기 위해 **디렉토리 경계 = 담당자 경계**로 설계했다. 레이어(프론트/백)로 일괄 분할하지 않고 **파이프라인 단계로 수직 분할**한 이유는, 이 프로젝트가 수집 → 요약 → 번역 → 피드의 순차 의존 구조여서 레이어로 자르면 대기와 충돌이 동시에 발생하기 때문이다. 단, 유일한 화면 영역인 사용자/관리자 프론트엔드는 분량이 1인 몫이 되므로 D가 전담한다.

각자 자신의 모듈 디렉토리 밖의 파일은 원칙적으로 수정하지 않는다 (공용 영역 취급은 §5 충돌 방지 규칙 1 참고).

| 담당 | 모듈 코드 | 담당 기능 | 소유 디렉토리 |
|---|---|---|---|
| **A** | `collector` | 뉴스 API 연동, 수집 스케줄 대상 정의, 키워드/카테고리/언론사 필터링, 중복 기사 제거, 수집 오류·재시도, 파이프라인 처리 현황 집계 API |  `newscollect/*` |
| **B** | `ai` | LLM 요약 생성(한 줄/3줄/상세), 다국어 번역, 요약 검수 플래그, 요약/번역 결과 영구 저장, 프로바이더별 호출량·비용 기록 및 임계치 알림 | `backend/app/modules/ai/*`, `backend/app/batch/{summarize,translate}.py` |
| **C** | `feed` (Backend) | 회원가입/로그인(Redis 세션), 관심 태그 등록·관리, 콘텐츠 큐레이션 배치, 뉴스 피드 조회 API, 원문 링크 제공, 데이터 보관 정책 배치 | `backend/app/modules/{auth,feed}/*`, `backend/app/batch/{curate,retention}.py`, `backend/app/db/migrations` |
| **D** | `web` (Frontend) | React 앱 전체 — 로그인/회원가입, 마이페이지, 관심 태그 설정, 피드 목록/상세, 북마크, 관리자 모니터링·비용 대시보드 | `frontend/src/**` (아래 공용 영역 제외) |
| 공용 | `_shared` | 소유자를 두지 않는다. 누구나 고치되 팀에 알린다 (§5 충돌 방지 규칙 1). 공용 컴포넌트/라우팅/디자인 토큰, DB 세션, 공통 예외/로깅, 배치 엔트리포인트, Terraform | `backend/app/{core,db,common}`, `backend/app/main.py`, `frontend/src/{routes,constants}`, `frontend/src/components/common`, `frontend/src/api/client.ts`, `frontend/src/types/common`, `infra/`, `.github/workflows/` |

### 프론트/백 경계 운영 (C ↔ D)

C�� D는 같은 기능을 양쪽에서 나눠 갖기 때문에 **API 계약이 곧 인터페이스**다.

- 화면 하나당 계약을 먼저 확정한다: `docs/api-contracts/feed.md`, `auth.md`, `admin.md`
- **API 명세의 기준은 D다.** 화면이 필요로 하는 응답 형태를 D가 계약 문서로 먼저 제시하고, C는 그 명세에 맞춰 백엔드를 구현한다. 명세와 구현이 어긋나면 명세가 아니라 C의 코드를 고친다. 구현상 명세를 지킬 수 없으면 임의로 응답을 바꾸지 말고 D에게 계약 변경을 요청한다.
- 계약 PR은 **C·D 두 명이 모두 승인**해야 머지된다. 계약 없이 시작한 구현은 반려.
- D는 계약 기준 mock으로 화면을 먼저 만들고, C의 API가 붙으면 mock을 제거한다.
- 응답 필드명·null 규칙·페이지네이션 방식은 계약 문서가 유일한 기준이며, 구현이 다르면 계약이 아니라 코드를 고친다.
- 관리자 대시보드가 쓰는 집계 API는 A(파이프라인 현황)와 B(비용/사용량)가 각각 제공한다. D는 화면만 담당하되 필요한 응답 형태를 계약으로 먼저 요청한다.

### 테스트

**통합 이후 각 담당이 자신의 모듈을 각자 테스트한다.** 별도 QA 담당을 두지 않는다.

- 각자 자기 모듈 디렉토리 하위에 `tests/`를 두고 최소 정상 경로 1개 + 실패 경로 1개를 유지한다.
- 남의 모듈 테스트를 수정하지 않는다. 남의 모듈 때문에 자기 테스트가 깨지면 이슈로 등록한다.
- 배치 로직은 실행기 없이 함수 단위로 테스트 가능해야 한다 (§2 참고).
- **모델·스키마·마이그레이션을 건드렸으면 로컬 MySQL 모드로도 한 번 돌린다** (§2.1). SQLite 모드만으로는 모델과 실제 스키마가 어긋난 것을 잡지 못한다.
- CI는 전체 테스트를 실행하되, 실패한 테스트의 수정 책임은 해당 모듈 소유자에게 있다.

### Alembic / 인프라 창구

- **DB 마이그레이션 창구는 C다.** `backend/app/db/migrations`는 C가 소유하며, 스키마 변경이 필요하면 이슈 등록 후 C가 revision을 생성한다 (이유는 §5 충돌 방지 규칙 5번).
- `infra/`(Terraform)와 `.github/workflows/`는 소유자를 고정하지 않는다. 디렉토리와 최소 스켈레톤만 확보해 두고, 작성 시점·담당은 팀에서 별도 합의한다.

## 4. 디렉토리 구조

```
newsbrief/
├── CLAUDE.md                      # 이 파일
├── .claude/skills/                # Claude Code용 모듈별 스킬 (아래 §6)
├── docs/                          # 요구사항 명세서, ERD, DB 스키마, API 계약
│   ├── db/{schema.sql, ERD.md, seed.sql}
│   └── api-contracts/{collector,ai,feed,auth,admin}.md
├── newscollect/                   # 뉴스 수집 파이프라인 (A 소유)
│   └── {naver_news,freenews,providers,details}/, main.py
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

### 커밋·푸시 승인 규칙 (최우선)
**Claude를 포함한 모든 자동화는 사용자의 명시적 요청 없이 커밋/푸시하지 않는다.** 코드 작성과 형상 반영은 분리된 단계다. 작업 완료 후에는 변경 요약 + 제안 커밋 메시지만 제시하고 사용자의 확인을 기다린다.

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
1. **자기 모듈 디렉토리 밖은 기본적으로 건드리지 않는다.** 공용 영역(`components/common`, `routes`, `core`, `db`, `common`, `main.py`, `client.ts`)은 여러 명이 함께 쓰므로, 고쳐야 하면 **고치되 무엇을 왜 바꿨는지 팀에 알린다.** 별도 PR로 분리하거나 전원 리뷰를 받을 필요는 없다 — 규모상 그 절차가 비용만 늘렸다.
2. 타입/스키마는 모듈별 `types/{module}` 또는 모듈 `schemas/`에만 선언하고, 다른 모듈이 참조해야 하면 `types/common`으로 승격 후 사용 (다른 모듈 폴더에서 직접 import 금지).
3. API 계약은 코드 작성 전 `docs/api-contracts/{module}.md`에 먼저 정의하고 PR로 리뷰받는다. C·D 사이의 계약은 양측 승인 필수.
4. **배치 로직은 파일 단위로 소유권을 나눈다.** 한 파일에 여러 담당의 배치를 섞지 않는다 (`collect.py`=A, `summarize.py`/`translate.py`=B, `curate.py`/`retention.py`=C).
5. **DB 스키마 변경은 C를 창구로 단일화한다.** 두 명이 각자 브랜치에서 Alembic revision을 만들면 head가 갈라져 머지 후 마이그레이션이 깨진다. 변경 필요 시 이슈 등록 → C가 revision 생성 → 머지 후 각자 rebase. 기존 마이그레이션 파일 직접 수정은 금지.
6. `requirements.txt` / `package.json`은 한 줄 추가도 자주 겹친다. 추가한 PR은 rebase 후 즉시 머지한다.

### PR 규칙
- PR 제목에 모듈 태그 포함: `[collector] 뉴스 API 클라이언트 구현`
- 본인 모듈 범위를 벗어난 변경이 diff에 섞여 있으면 반려
- 머지 전 최소 1인 리뷰
- PR 단위는 300줄 이하를 목표로 한다. 배치 로직은 커밋이 뭉치기 쉬우므로 "기능 1개 = PR 1개"를 의식적으로 지킨다.
- 이슈 제목은 **요구사항 명세서의 기능명을 그대로** 사용해 추적성을 유지한다. 라벨은 담당 영역(`collector`/`ai`/`feed`/`web`) + 중요도(`P-상`/`P-중`/`P-하`)만.
- `CODEOWNERS`에 §3 표의 디렉토리를 등록해 리뷰어를 자동 배정한다.

### 의존 순서와 병렬화
A → B → C → D는 데이터 의존이지만 **그대로 기다리면 4명이 직렬화된다.** 다음을 전제로 병렬 작업한다.

- 0주차에 넷이 함께: 리포 구조, FastAPI 스켈레톤, 로컬 MySQL·Redis 환경 합의(§2.1), 초기 마이그레이션(C가 스키마 전체를 한 번에 커밋), `.env.example`, 린트·포맷 설정, CI 워크플로, `docs/api-contracts/` 초안.
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
- **Backend**: 모듈 = `routers`(엔드포인트) / `schemas`(Pydantic) / `services`(비즈니스 로직) / `models`(SQLAlchemy) 4단 구조 고정. **라우터에 비즈니스 로직 작성 금지. LLM 호출은 `modules/ai/services` 밖에서 하지 않는다.**
- **SQLAlchemy 모델은 도메인별 파일로 분리한다** (`models/article.py`, `models/user.py` …). 단일 `models.py`는 충돌의 온상이므로 만들지 않는다.
- **배치는 실행기 비의존으로 작성한다** (§2). 스케줄 관련 상수(실행 시각 등)는 설정으로 외부화한다.
- **네이밍**: 프론트 폴더는 kebab-case, 백엔드 파이썬 모듈은 snake_case — 언어 컨벤션에 맞춰 의도적으로 다르게 유지. DB 테이블/컬럼은 snake_case, 테이블명은 복수형.
- **시크릿**: API 키·DB 접속정보를 코드/설정 파일에 절대 하드코딩하지 않는다. 로컬은 `.env`(gitignore), 배포는 시크릿 관리 도구. `.env.example`만 커밋한다.
- **로깅**: 배치 처리 결과는 print가 아니라 `batch_jobs` / `job_logs` 테이블에 기록한다 (요구사항: 수집 오류 처리).
- **디자인 토큰** (전 모듈 공통, 임의 색상 사용 금지):
  - 프라이머리 딥네이비 `#1F3A5F` / 배경(밝음) `#FAFAF8` / 서페이스(톤다운) `#EFEDE7` / 강조 `#C2410C` / 상태색: 성공 `green-600`, 경고 `amber-600`, 오류 `red-600`

## 8. 확정된 결정 사항 (스키마 V2) / 남은 미결 사항

`docs/db/schema.sql` 검토 중 확정된 사항이다. 스키마는 **V2**로 갱신했고, 각 모듈 SKILL.md도 반영했다.

1. **`article_chunks` 테이블을 제거했다.** 요구사항 "긴 기사 청크 분할"이 스코프에서 빠졌으므로, 분할 저장 테이블과 `summaries.chunk_count` 컬럼을 모두 삭제한다. (~~V1 초안의 청크 분할·병합 요약 설계는 이 문서로 대체된다~~ — B 담당은 청크 병합 로직을 구현하지 않는다)
2. **배치 실행 기술은 미정이며, 스키마도 특정 기술에 결합시키지 않는다.** `batch_jobs.celery_task_id`는 `batch_jobs.task_ref`(실행기 식별자, 기술 중립)로 변경했다. Redis 키 설계에서도 브로커 용도는 제외하고 세션/캐시/락만 남긴다.
3. **중복 제거는 이중 방어로 확정.** Redis `dedup:url:{yyyymmdd}` SET으로 INSERT 전 1차 필터링하되, 최종 보증은 `articles.url_hash`(정규화 URL의 SHA-256) 유니크 인덱스가 담당한다. Redis만 믿는 구현 금지. (A 담당)
   - V1.1에서는 이 규칙이 **구조적으로 지켜지지 않고 있었다.** 파티셔닝 때문에 유니크가 `(url_hash, published_at)` 복합이어야 했고, 같은 기사의 `published_at`이 재수집 시 조금이라도 달라지면(언론사 기사 수정, API 응답 편차, 시각 정규화 차이) 중복 INSERT가 통과했다. Redis 1차 필터도 키가 날짜 단위라 날짜가 바뀐 뒤의 재수집을 막지 못해 두 방어선이 같은 지점에서 함께 뚫렸다. V2가 파티셔닝을 제거하면서 `UNIQUE (url_hash)` 단일로 돌아와 이제 규칙대로 동작한다.
4. **재호출 방지 유니크 키 확정.** `summaries`는 `(article_id, summary_type)`, `translations`는 `(summary_id, target_language)` 유니크. 같은 조합이 두 번 생성되면 곧 비용 중복이므로 UPSERT로 처리한다. (B 담당)
5. **`feed_items` INSERT는 C가 소유한다.** B는 `summaries` / `translations`까지만 쓰고, 피드 행 생성은 C의 `curate.py` 배치가 담당한다. 이 경계를 넘는 PR은 반려한다.
6. **Redis는 세션/캐시 전용.** 요약·번역 본문을 Redis에만 두는 구현 금지 (영구 저장은 MySQL). Redis 키 설계는 `docs/db/schema.sql` 하단 주석 참고.
7. **테스트는 통합 이후 각 담당이 자기 모듈을 각자 수행한다.** 전담 QA/인프라 담당을 두지 않는다. (§3 테스트 항목)
8. **Terraform은 공간만 확보한다.** `infra/` 디렉토리와 스켈레톤만 두고, 작성 담당·시점은 별도 합의로 미룬다.

#### V2에서 추가로 확정한 사항

9. **`articles` 파티셔닝을 제거하고 FK를 살린다.** 기존 "파티셔닝 vs FK" 미결 사항을 FK 쪽으로 확정했다. 일 수천 건 규모에서는 보관 정책을 `BATCH_DELETE`로 처리해도 충분하고, 참조 무결성을 DB가 보장하는 편이 애플리케이션 부담이 적다. PK가 `(id, published_at)` 복합에서 `id` 단일로 돌아왔고, `article_id` FK 7개가 복구됐다. 3번의 중복 제거 정상화가 부수 효과로 따라온다. (C 담당)
10. **단일 프로바이더(Bedrock) 전제를 버리고 다중 프로바이더로 간다.** `summaries.model_id` / `translations.model_id` / `ai_invocations.model_id`를 `provider` + `model_name` 두 컬럼으로 분리했다. `ai_invocations`에 `is_token_estimated`(프로바이더가 토큰 수를 주지 않아 추정한 경우), `is_fallback`(기본 모델 실패로 대체 모델이 처리한 경우)을 추가하고 `status`에 `TIMEOUT` / `RATE_LIMITED`를 넣어 실패 원인을 구분한다. **스키마에도 코드에도 특정 클라이언트 라이브러리명을 박지 않는다** — 2번(실행기 비결합)과 같은 기준이다. (B 담당)
11. **원문 삭제가 LLM 결과를 연쇄 삭제하지 못하게 막는다.** `articles` → `summaries` / `feed_items` FK를 `ON DELETE RESTRICT`로 걸었다. 요약이 남아 있는 기사는 삭제 자체가 실패한다. 원문은 URL로 재수집할 수 있지만 요약은 LLM을 다시 호출해야 만들어지므로, 이건 성능이 아니라 **비용 사고** 방지다. `ARTICLES` 보관 정책 구현 방식은 아래 미결 사항 참고. (C 담당)
12. **보조 인덱스는 스키마 본문에서 분리한다.** `schema.sql`에는 업무 규칙에 해당하는 제약(PK / FK / UNIQUE)만 남기고, 조회 성능용 `KEY`와 `FULLTEXT`는 파일 하단 주석에 추가 후보로 정리했다. 실제 쿼리를 `EXPLAIN`으로 확인한 뒤 `ALTER`로 붙인다. FK 컬럼에는 InnoDB가 인덱스를 자동 생성하므로 중복 생성하지 않는다.
13. **`retention_policies` 조정.** `strategy`에서 `PARTITION_DROP`을 제거했다(파티셔닝을 뺐으므로 실행 불가능한 값이고, 남겨 두면 관리자 화면에 고를 수 없는 선택지가 뜬다). `target_entity`에는 `INVOCATIONS`를 추가해 `ai_invocations` 보관 정책을 표현할 수 있게 했다. (C 담당)
14. **`ARTICLES` 보관 정책은 hard delete다.** 11번의 `RESTRICT` 때문에 원문을 지우려면 요약을 먼저 버려야 한다. soft purge(본문만 NULL) 대신 **"요약을 버린다"는 판단을 명시적으로 먼저 내리는** 쪽을 택했다. 순서는 `DELETE summaries`(→ `translations` / `feed_items` CASCADE) → `DELETE articles`(→ `article_tags` CASCADE) 고정이며, 순서를 어기면 RESTRICT에 걸려 실패한다. 되돌릴 수 없으므로 `dry_run`으로 대상 건수를 먼저 확인할 수 있게 했고 요약/원문 건수를 `job_logs`에 남긴다. 구현은 `modules/feed/services/retention_service.py`. (C 담당)
15. **초기 마이그레이션을 V2 기준으로 한 리비전에 담았다.** `backend/app/db/migrations/versions/0001_v2_initial_schema.py`가 17개 테이블을 모두 생성한다. 모델이 스키마 전체를 덮지 않으므로(A·B 테이블 6개는 모델 없음) **autogenerate가 아니라 `schema.sql`을 기준으로 손으로 작성했다.** `env.py`의 `include_object`가 메타데이터에 없는 테이블을 비교 대상에서 제외해, 이후 autogenerate가 A·B 테이블에 DROP을 제안하는 사고를 막는다. (C 담당)

### 남은 미결 사항
- **배치 실행 기술 선정** — 스케줄러/큐를 무엇으로 할지 미정. 하루 3회 고정 배치라는 요구사항만 확정. 선정 전까지 §2 규칙(실행기 비의존)을 지킨다. (전원 합의 사항)
- **요약 3종 저장 여부** — 현재 스키마는 한 줄/3줄/상세를 별도 row로 두지만, 배치에서 세 종류를 다 만들면 LLM 호출이 3배가 된다. "상세 1건만 저장 + 짧은 버전은 프런트에서 절단" 안과 비교 검토 필요. (B·D 협의, 비용 추정 후 결정)
- **`cost_budgets`의 기간별 유니크** — V2는 `UNIQUE (period_type)`을 뒀다. `DAILY`/`MONTHLY` 각 1행만 허용되므로 프로바이더별 예산을 만들 수 없는데, §8-10으로 프로바이더가 여럿이 된 이상 "OpenAI 일일 한도"와 "Anthropic 일일 한도"를 따로 두고 싶어질 수 있다. 필요해지면 `provider` 컬럼 추가 + `UNIQUE (period_type, provider)`로 넓히되, MySQL 유니크는 `NULL` 중복을 허용하므로 "전체 예산"의 유일성은 따로 보장해야 한다. 초기에는 전체 한도 하나로 충분하다고 보고 현행 유지. (B 담당)
- **인덱스 추가 시점** — §8-12로 보조 인덱스가 전부 빠졌다. 성능 손실이 가장 큰 것은 `idx_feed_list`다. 피드 목록은 앱에서 가장 빈번한 쿼리이고 `uk_feed(user_id, article_id)`로 `user_id` 필터는 타지만 정렬은 filesort가 된다. 일 수천 건 규모에서는 문제없으나, 데이터가 늘면 `schema.sql` 하단 후보 중 이것부터 붙인다. (C 담당)
- **토큰 제한 초과 기사 처리** — 청크 분할을 하지 않기로 했으므로 대안을 정해야 한다. (a) `articles.status='FAILED'` + `job_logs.error_code='TOKEN_LIMIT_EXCEEDED'`로 스킵, (b) 본문 앞부분만 잘라 요약하고 `summaries.is_truncated` 플래그 추가. (b)를 택하면 스키마 변경이 필요하다. (B 담당)
- **번역 지원 언어 목록** — `users.preferred_language`와 `translations.target_language`의 허용 값 확정 필요. 지원 언어가 늘어날수록 호출 비용이 선형 증가하므로 초기에는 최소 집합으로 시작. (B·C 협의)
- **기본 프로바이더·모델 선정** — 프로바이더와 모델 ID를 환경변수로 주입하고 `summaries.provider` / `summaries.model_name`에 실제 사용값을 기록한다는 원칙만 확정(§8-10). 어떤 프로바이더·모델을 기본값으로 쓸지, 폴백 순서를 어떻게 둘지는 미결. (B 담당)
- **비용/실패 알림 채널** — `cost_budgets.notify_channel`의 실제 전송 수단과 배치 실패 알림 경로 미정. (B 담당)
- **Terraform·CI/CD 담당과 착수 시점** — 미정. (전원 합의 사항)

## 9. Claude에게 주는 전역 지시사항

- **사용자가 명시적으로 지시하기 전에는 절대 `git commit` / `git push`를 실행하지 않는다.** 작업이 끝나면 변경 파일 목록과 제안 커밋 메시지(§5 컨벤션)까지만 정리해 보고하고 대기한다. 브랜치 생성·스테이징(`git add`)도 사용자 요청이 있을 때만 한다. "커밋해줘", "푸시해줘" 같은 직접 지시만 승인으로 간주하며, "이 작업 끝내줘" 류의 포괄적 요청은 커밋 승인이 아니다. PR 생성·머지도 동일하다.
- 항상 **§3 소유권 표에 명시된 디렉토리 범위 안에서만** 파일을 생성/수정한다. 범위를 벗어나야 하는 작업이면 먼저 사용자에게 알린다.
- **조회 경로에 LLM 호출을 넣지 않는다.** 피드/상세 조회 API를 구현할 때 요약이 없으면 생성하는 코드를 절대 쓰지 말고, 저장된 결과가 없으면 해당 기사를 응답에서 제외하거나 명시적 상태값으로 반환한다. 프로바이더가 여럿이 되면 이 원칙의 중요도는 더 올라간다.
- **배치 실행 기술을 임의로 선택하지 않는다.** 특정 스케줄러/큐 라이브러리를 설치하거나 데코레이터·설정 파일을 추가하지 말고, 실행기에 의존하지 않는 함수로 작성한 뒤 트리거가 필요하면 사용자에게 알린다.
- **스키마 변경이 필요한 작업**이면 코드를 먼저 쓰지 않고, 변경 내용을 정리해 사용자에게 알린 뒤 C 창구를 통하도록 안내한다. Alembic revision을 임의 생성하지 않는다.
- 새 API를 만들 때는 먼저 `docs/api-contracts/{module}.md`에 계약이 있는지 확인하고, 없으면 만들어 사용자 확인을 받은 뒤 구현한다. 프론트 작업 시 계약에 없는 응답 필드를 가정하지 않는다.
- API 키·DB 접속정보 등 시크릿을 코드나 커밋에 포함하지 않는다. 예시가 필요하면 `.env.example`에 플레이스홀더로만 쓴다.
- 배치를 구현할 때는 실행 이력(`batch_jobs`)과 오류(`job_logs`) 기록, LLM 호출 시 `ai_invocations` 기록을 항상 함께 남긴다.
- 모듈 코드를 작성하면 같은 모듈 `tests/`에 최소 테스트를 함께 추가한다 (§3 테스트).
- 커밋 메시지는 §5 컨벤션을 따른다.
