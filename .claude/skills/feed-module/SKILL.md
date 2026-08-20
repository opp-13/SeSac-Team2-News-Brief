---
name: feed-module
description: NewsBrief 리포지토리에서 C 담당(feed 모듈) 작업을 할 때 반드시 먼저 로드한다. 회원가입/로그인(Redis 세션), 관심 태그 등록·관리, 콘텐츠 큐레이션 배치(curate.py), 뉴스 피드 조회·상세 API, 원문 링크 제공, 데이터 보관 정책 배치(retention.py), Alembic 마이그레이션이 대상이다. "피드", "태그", "로그인", "세션", "큐레이션", "보관 정책", "마이그레이션", "스키마 변경", "feed_items", "auth API" 중 하나라도 언급되면 이 스킬을 로드한다. 백엔드 API를 만들거나 고치는 작업이면 모듈명이 명시되지 않았더라도 일단 이 스킬을 확인한다.
---

# feed-module (C 담당)

`CLAUDE.md`의 전역 규칙이 항상 우선한다. 이 문서는 C 모듈에만 적용되는 세부 규칙이다.

## 0. 매 작업 전 확인 (순서대로)

1. **커밋/푸시하지 않는다.** 사용자가 "커밋해줘 / 푸시해줘"라고 직접 지시하기 전에는 `git add`, `git commit`, `git push`, PR 생성을 절대 실행하지 않는다. 작업이 끝나면 변경 파일 목록 + 제안 커밋 메시지만 보고하고 멈춘다.
2. **작업 대상이 C 소유 디렉토리 안인가?** (아래 §1) 밖이면 코드를 쓰기 전에 사용자에게 알린다.
3. **새 API인가?** → `docs/api-contracts/{feed,auth,admin}.md`에 D가 확정한 명세가 있는지 먼저 확인한다. 없으면 구현하지 말고 사용자에게 알린다 (§3).
4. **스키마 변경이 필요한가?** → Alembic revision을 바로 만들지 말고 변경안을 먼저 정리해 보고한다 (§5).
5. **조회 경로에 LLM 호출이 끼어들 여지가 있는가?** → 있으면 설계가 틀린 것이다 (§4).

## 1. 소유 범위

**쓰기 가능**

```
backend/app/modules/auth/{routers,schemas,services,models}/
backend/app/modules/feed/{routers,schemas,services,models}/
backend/app/batch/curate.py
backend/app/batch/retention.py
backend/app/db/migrations/          # Alembic — 팀 전체의 스키마 창구
backend/app/modules/{auth,feed}/tests/
```

**읽기만 (수정 금지)**

- `newscollect/*` (A), `backend/app/modules/ai/*`, `batch/{summarize,translate}.py` (B), `frontend/src/**` (D)
- 남의 모듈 `tests/`는 절대 수정하지 않는다. 남 때문에 내 테스트가 깨지면 이슈로 등록한다.

**공용 (소유자 없음 — 고치되 알린다)**

- `backend/app/{core,db,common}`, `backend/app/main.py`, `infra/`, `.github/workflows/`
- 여러 명이 함께 쓰는 파일이므로 무엇을 왜 바꿨는지 팀에 알린다. 별도 PR이나 전원 리뷰는 필요 없다 (CLAUDE.md §5 충돌 방지 규칙 1).

**다른 모듈의 타입/스키마를 그 폴더에서 직접 import 하지 않는다.** 공유가 필요하면 공용 승격 후 사용.

## 2. 담당 기능

| 기능 | 위치 |
|---|---|
| 회원가입/로그인/로그아웃, Redis 세션 | `modules/auth/` |
| 관심 태그 등록·조회·삭제 | `modules/feed/`(또는 `auth`) — 계약 문서의 경로 기준 |
| 뉴스 피드 목록/상세 조회, 원문 링크 제공 | `modules/feed/` |
| 콘텐츠 큐레이션 배치 (`feed_items` 생성) | `batch/curate.py` |
| 데이터 보관 정책 배치 | `batch/retention.py` |
| DB 마이그레이션 | `db/migrations/` |

## 3. API 명세는 D를 따른다 (이 모듈의 핵심 운영 규칙)

- 화면을 소비하는 쪽이 D이므로 **`docs/api-contracts/{feed,auth,admin}.md`의 명세가 단일 기준**이고, C는 거기에 맞춰 구현한다.
- 응답 필드명, 카멜/스네이크 표기, null 허용 여부, 페이지네이션 방식, 에러 응답 형태, 상태 코드는 **모두 계약 문서를 그대로 따른다.** 백엔드 관례가 더 낫다는 이유로 바꾸지 않는다.
- 구현 결과가 명세와 다르면 **명세가 아니라 C의 코드를 고친다.**
- 명세대로 구현이 불가능하거나 비용/성능상 문제가 있으면, 응답을 임의로 변형하지 말고 **작업을 멈추고 사용자에게 보고**한다 → D에게 계약 변경 요청 → 계약 PR(C·D 양측 승인) 후 구현.
- **계약에 없는 API/필드를 먼저 만들지 않는다.** 계약 문서가 없는 엔드포인트 요청을 받으면 구현 전에 사용자에게 알린다.
- DB 컬럼명을 응답에 그대로 흘려보내지 않는다. 항상 Pydantic 스키마(`schemas/`)에서 계약 형태로 변환한다.

## 4. 절대 금지 (위반 시 설계 오류)

1. **조회 시점 LLM 호출 금지.** 피드/상세 API에서 요약이 없다고 생성하는 코드는 성능 문제가 아니라 비용 사고다. 저장된 요약/번역이 없으면 해당 기사를 응답에서 제외하거나 명시적 상태값으로 반환한다. `modules/ai` 서비스를 조회 경로에서 import 하지 않는다.
2. **`summaries` / `translations` 테이블에 INSERT/UPDATE 금지.** 그 쓰기 소유자는 B다. C는 읽기만 한다. 반대로 **`feed_items` INSERT는 C만** 한다 (`curate.py`). **DELETE 예외는 보관 배치 하나뿐이다** — `retention_service.py`가 hard delete 순서상 `summaries`를 먼저 지운다 (§7).
3. **배치 실행기 결합 금지.** `curate.py` / `retention.py`는 인자를 받아 결과를 반환하는 순수 함수/서비스 호출로 작성한다. 스케줄러·큐 라이브러리 설치, 데코레이터 부착, 브로커 설정 파일 추가 금지. 실행 시각 등 스케줄 상수는 설정으로 외부화한다.
4. **라우터에 비즈니스 로직 금지.** `routers`는 입출력과 의존성 주입만, 로직은 `services`.
5. **단일 `models.py` 금지.** 도메인별 파일로 분리 (`models/user.py`, `models/feed_item.py` …).
6. **Redis에 본문/요약 영구 저장 금지.** Redis는 세션·피드 캐시·락 전용, 영구 저장은 MySQL.
7. **시크릿 하드코딩 금지.** `.env`(gitignore) + `.env.example` 플레이스홀더만.
8. **기존 마이그레이션 파일 직접 수정 금지.** 항상 새 revision.

## 5. DB / Alembic (C가 팀 창구)

- `backend/app/db/migrations`는 C 소유이며, **A·B·D의 스키마 변경 요청도 C가 revision을 만든다.** head 분기를 막기 위한 규칙이다.
- 스키마 변경이 필요하면 Claude는 **revision을 임의 생성하지 않고** 변경 내용(테이블/컬럼/인덱스, 이유, 영향 모듈)을 정리해 사용자에게 먼저 보고한다.
- 초기 리비전은 `versions/0001_v2_initial_schema.py`(V2 전체 17개 테이블)다. 실행은 `backend/`에서 `.venv/bin/alembic upgrade head`.
- **`--autogenerate`를 그냥 믿지 않는다.** 모델이 스키마 전체를 덮지 않는다(A·B 테이블 6개는 모델이 없다). `env.py`의 `include_object`가 DROP 제안을 막고 있지만, 생성된 리비전은 항상 눈으로 확인하고 `schema.sql`과 대조한다.
- 접속 정보는 `alembic.ini`가 아니라 `app.core.config`의 `DATABASE_URL`에서 읽는다. `alembic.ini`에 URL을 적지 않는다.
- 기준 문서는 `docs/db/schema.sql`(V2)과 `docs/db/ERD.md`. 코드가 스키마와 다르면 스키마를 확인하고 보고한다.
- V2 확정 사항 중 C가 기억할 것:
  - `article_chunks` 없음, `batch_jobs.task_ref`(기술 중립), `feed_items` 소유권은 C.
  - `articles`는 파티셔닝하지 않는다. PK는 `id` 단일이고 `article_id` FK가 살아 있다.
  - `articles` → `summaries` / `feed_items` FK가 `ON DELETE RESTRICT`다. **요약이 남아 있는 기사는 삭제되지 않는다** — `retention.py`에서 `DELETE FROM articles`를 그냥 부르면 실패한다 (§10 참고).
  - `feed_items.summary_id`는 NOT NULL이다. 요약 없는 기사는 피드 행을 만들지 않는다.
  - `retention_policies.strategy`는 `BATCH_DELETE`만 있다. `PARTITION_DROP`은 V2에서 제거됐다.
  - 보조 인덱스는 스키마 본문에 없다. 필요하면 `schema.sql` 하단 후보에서 `ALTER`로 붙인다.
  - 요약/번역 모델 정보는 `model_id`가 아니라 `provider` + `model_name` 두 컬럼이다 (읽기 전용, B 소유).

## 6. 세션 / Redis

- 로그인 세션은 Redis. 세션 키·TTL 설계는 `docs/db/schema.sql` 하단 Redis 키 주석을 따른다.
- 피드 캐시를 쓰더라도 **캐시 미스가 LLM 호출로 이어지는 경로를 절대 만들지 않는다** (캐시 미스 → MySQL 조회까지만).
- 비밀번호는 해시 저장. 평문·복호화 가능 암호화 금지.

## 7. 배치 작성 규칙 (`curate.py`, `retention.py`)

- 실행 이력은 `batch_jobs`, 오류는 `job_logs`에 기록한다. `print`로 끝내지 않는다.
- 함수 단위로 실행기 없이 테스트 가능해야 한다.
- `curate.py`: 사용자 관심 태그 ↔ 기사 매칭으로 `feed_items` 생성. 요약/번역이 준비되지 않은 기사는 피드 행을 만들지 않는다.
- `retention.py`: 보관 정책에 따른 삭제. 삭제 대상 건수를 로그로 남기고, 되돌릴 수 없는 삭제는 배치 단위로 카운트를 기록한다.
- **`ARTICLES` 정책은 hard delete로 확정됐다.** V2가 `articles` → `summaries` / `feed_items`를 `ON DELETE RESTRICT`로 묶었으므로 순서가 고정이다.
  1. `DELETE summaries` → `translations` / `feed_items`가 FK CASCADE로 따라간다
  2. `DELETE articles` → `article_tags`가 FK CASCADE로 따라간다

  순서를 어기면 RESTRICT에 걸려 실패한다. 되돌릴 수 없으므로 `dry_run`을 먼저 지원하고 요약/원문 건수를 각각 반환한다.
- **소유권 예외**: §4-2의 "C는 `summaries`를 읽기만 한다"는 생성 소유권 얘기다. **보관 배치만 `summaries`를 DELETE 한다** — 위 순서 때문에 불가피하고, CLAUDE.md §3이 보관 정책을 C 담당으로 두고 있다. `retention_service.py` 밖에서는 하지 않는다.
- 개발 초기에는 `docs/db/seed.sql`의 시드 요약/번역 데이터로 진행한다 (B의 실제 결과를 기다리지 않는다).

## 8. 테스트

- `modules/{auth,feed}/tests/`에 **최소 정상 경로 1개 + 실패 경로 1개**를 유지한다.
- 배치는 DB/실행기 없이 함수 단위로 검증 가능한 형태로 테스트한다.
- 모듈 코드를 새로 쓰면 같은 PR에 테스트를 함께 넣는다.
- 기본은 SQLite in-memory다: `.venv/bin/python -m pytest app`
- **모델·스키마·마이그레이션을 건드렸으면 로컬 MySQL 모드로도 돌린다** (CLAUDE.md §2.1):
  `TEST_DATABASE_URL="mysql+pymysql://..." .venv/bin/python -m pytest app`
  SQLite 모드는 모델로 테이블을 만들기 때문에 **모델이 실제 스키마와 어긋나도 통과한다.**
  MySQL 모드는 Alembic이 올린 스키마에 그대로 붙으므로 그 어긋남을 잡는다 (`app/db/testing.py`).
- Docker는 쓰지 않는다. 로컬에 설치한 MySQL·Redis에 직접 붙는다.

## 9. 커밋 / PR (실행은 사용자 승인 후에만)

```
feat(feed): 관심 태그 기반 피드 조회 API 추가
feat(auth): Redis 세션 로그인 구현
fix(feed): 페이지네이션 커서 계산 오류 수정
```

- `module` 값은 `auth` 또는 `feed` (마이그레이션은 관련 모듈 태그 사용, 공용 변경은 `shared`).
- 브랜치: `feature/feed/{task}`, `feature/auth/{task}`, `fix/feed/{issue}`.
- PR 제목: `[feed] ...` / `[auth] ...`, 300줄 이하 목표, 기능 1개 = PR 1개.
- 이슈 제목은 요구사항 명세서의 기능명 그대로.
- **다시 강조: Claude는 위 커밋/브랜치/PR을 사용자 지시 없이 실행하지 않는다. 제안까지만 한다.**

## 10. 미결 사항 (임의로 결정하지 말 것)

- ~~`articles` 파티셔닝 vs FK~~, ~~`ARTICLES` 보관 정책 방식~~ — **둘 다 확정됐다.** FK 유지 + hard delete다 (아래 §7 참고).
- **번역 지원 언어 목록** (B·C 협의) — `users.preferred_language` 허용 값을 코드에 임의로 박지 않는다.
- **배치 실행 기술** (전원 합의) — 선정 전까지 §4-3 유지.
- **요약 3종 저장 여부** (B·D 협의) — 피드 응답이 어떤 요약 타입을 쓰는지는 계약 문서를 따른다.
