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
5. **조회 경로에 Bedrock 호출이 끼어들 여지가 있는가?** → 있으면 설계가 틀린 것이다 (§4).

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

**공용 (별도 PR + 전원 리뷰 필요)**

- `backend/app/{core,db,common}`, `backend/app/main.py`, `infra/`, `.github/workflows/`
- 라우터 등록 등으로 `main.py`를 건드려야 하면 기능 PR에 섞지 말고 분리한다.

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

1. **조회 시점 Bedrock 호출 금지.** 피드/상세 API에서 요약이 없다고 생성하는 코드는 성능 문제가 아니라 비용 사고다. 저장된 요약/번역이 없으면 해당 기사를 응답에서 제외하거나 명시적 상태값으로 반환한다. `modules/ai` 서비스를 조회 경로에서 import 하지 않는다.
2. **`summaries` / `translations` 테이블에 INSERT/UPDATE 금지.** 그 쓰기 소유자는 B다. C는 읽기만 한다. 반대로 **`feed_items` INSERT는 C만** 한다 (`curate.py`).
3. **배치 실행기 결합 금지.** `curate.py` / `retention.py`는 인자를 받아 결과를 반환하는 순수 함수/서비스 호출로 작성한다. 스케줄러·큐 라이브러리 설치, 데코레이터 부착, 브로커 설정 파일 추가 금지. 실행 시각 등 스케줄 상수는 설정으로 외부화한다.
4. **라우터에 비즈니스 로직 금지.** `routers`는 입출력과 의존성 주입만, 로직은 `services`.
5. **단일 `models.py` 금지.** 도메인별 파일로 분리 (`models/user.py`, `models/feed_item.py` …).
6. **Redis에 본문/요약 영구 저장 금지.** Redis는 세션·피드 캐시·락 전용, 영구 저장은 MySQL.
7. **시크릿 하드코딩 금지.** `.env`(gitignore) + `.env.example` 플레이스홀더만.
8. **기존 마이그레이션 파일 직접 수정 금지.** 항상 새 revision.

## 5. DB / Alembic (C가 팀 창구)

- `backend/app/db/migrations`는 C 소유이며, **A·B·D의 스키마 변경 요청도 C가 revision을 만든다.** head 분기를 막기 위한 규칙이다.
- 스키마 변경이 필요하면 Claude는 **revision을 임의 생성하지 않고** 변경 내용(테이블/컬럼/인덱스, 이유, 영향 모듈)을 정리해 사용자에게 먼저 보고한다.
- 기준 문서는 `docs/db/schema.sql`(V1.1)과 `docs/db/ERD.md`. 코드가 스키마와 다르면 스키마를 확인하고 보고한다.
- V1.1 확정 사항 중 C가 기억할 것: `article_chunks` 없음, `batch_jobs.task_ref`(기술 중립), `feed_items` 소유권은 C.

## 6. 세션 / Redis

- 로그인 세션은 Redis. 세션 키·TTL 설계는 `docs/db/schema.sql` 하단 Redis 키 주석을 따른다.
- 피드 캐시를 쓰더라도 **캐시 미스가 Bedrock 호출로 이어지는 경로를 절대 만들지 않는다** (캐시 미스 → MySQL 조회까지만).
- 비밀번호는 해시 저장. 평문·복호화 가능 암호화 금지.

## 7. 배치 작성 규칙 (`curate.py`, `retention.py`)

- 실행 이력은 `batch_jobs`, 오류는 `job_logs`에 기록한다. `print`로 끝내지 않는다.
- 함수 단위로 실행기 없이 테스트 가능해야 한다.
- `curate.py`: 사용자 관심 태그 ↔ 기사 매칭으로 `feed_items` 생성. 요약/번역이 준비되지 않은 기사는 피드 행을 만들지 않는다.
- `retention.py`: 보관 정책에 따른 삭제/아카이빙. 삭제 대상 건수를 로그로 남기고, 되돌릴 수 없는 삭제는 배치 단위로 카운트를 기록한다.
- 개발 초기에는 `docs/db/seed.sql`의 시드 요약/번역 데이터로 진행한다 (B의 실제 결과를 기다리지 않는다).

## 8. 테스트

- `modules/{auth,feed}/tests/`에 **최소 정상 경로 1개 + 실패 경로 1개**를 유지한다.
- 배치는 DB/실행기 없이 함수 단위로 검증 가능한 형태로 테스트한다.
- 모듈 코드를 새로 쓰면 같은 PR에 테스트를 함께 넣는다.

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

- **`articles` 파티셔닝 vs FK** (C 담당, 예상 기사량 확정 후) — 보관 정책 구현이 여기에 걸리면 한쪽을 가정하고 진행하지 말고 보고한다.
- **번역 지원 언어 목록** (B·C 협의) — `users.preferred_language` 허용 값을 코드에 임의로 박지 않는다.
- **배치 실행 기술** (전원 합의) — 선정 전까지 §4-3 유지.
- **요약 3종 저장 여부** (B·D 협의) — 피드 응답이 어떤 요약 타입을 쓰는지는 계약 문서를 따른다.
