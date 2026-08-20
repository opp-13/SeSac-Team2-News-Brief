# C 모듈 산출물 배치 가이드

> 받은 `newsbrief/` 폴더는 **레포 루트와 같은 구조**다. 경로를 하나씩 옮길 필요 없이 레포 루트 위에 그대로 덮으면 된다.
> 전부 신규 파일이라 기존 파일과 충돌하지 않는다 (아래 §4의 "직접 넣지 않은 것" 제외).

## 1. 한 번에 옮기기

```bash
# <다운로드경로> = 받은 newsbrief 폴더, <레포루트> = 로컬 newsbrief 레포
cd <레포루트>
git switch -c feature/feed/module-skeleton     # 브랜치 생성도 원하면 실행

cp -r <다운로드경로>/newsbrief/backend ./
cp -r <다운로드경로>/newsbrief/docs ./

git status                                      # 신규 파일 43개만 잡히는지 확인
```

Windows PowerShell:

```powershell
Copy-Item <다운로드경로>\newsbrief\backend -Destination . -Recurse -Force
Copy-Item <다운로드경로>\newsbrief\docs    -Destination . -Recurse -Force
```

`cp -r`은 **같은 이름의 파일만 덮어쓴다.** 위 목록에 없는 기존 파일(`main.py`, `core/`, `db/session.py` 등)은 건드리지 않는다.

**커밋·푸시는 하지 않는다.** 배치 후 `git status`까지만 확인하고, 커밋은 직접 지시할 때 진행한다.

---

## 2. 최종 배치 위치 (트리)

```
newsbrief/
├── backend/app/
│   ├── batch/
│   │   ├── curate.py                    # C 소유 배치 (feed_items 생성)
│   │   └── retention.py                 # C 소유 배치 (보관 정책)
│   └── modules/
│       ├── auth/                        # ← 신규 디렉토리 (C 소유)
│       │   ├── __init__.py
│       │   ├── api_paths.py             # ★ 임시 API 경로 상수 (계약 확정 시 여기만 수정)
│       │   ├── dependencies.py          # 세션 인증 의존성 (get_current_user)
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   └── user.py              # users 테이블
│       │   ├── schemas/
│       │   │   ├── __init__.py
│       │   │   ├── base.py              # ★ camelCase 직렬화 베이스
│       │   │   └── auth.py              # ★ 임시 요청/응답 필드명
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── auth_service.py      # 가입/로그인/비번변경 로직
│       │   │   ├── password.py          # bcrypt 해시
│       │   │   └── session_service.py   # Redis 세션 CRUD
│       │   ├── routers/
│       │   │   ├── __init__.py
│       │   │   └── auth_router.py
│       │   └── tests/
│       │       ├── __init__.py
│       │       ├── conftest.py          # SQLite in-memory + FakeRedis
│       │       └── test_auth_service.py
│       └── feed/                        # ← 신규 디렉토리 (C 소유)
│           ├── __init__.py
│           ├── api_paths.py             # ★ 임시 API 경로 상수
│           ├── models/
│           │   ├── __init__.py
│           │   ├── tag.py               # tags / user_tags
│           │   ├── feed_item.py         # feed_items (INSERT는 C 전용)
│           │   ├── bookmark.py          # bookmarks (스키마 확인 필요)
│           │   └── read_only.py         # articles/summaries/translations 조회 전용
│           ├── schemas/
│           │   ├── __init__.py
│           │   ├── base.py              # ★ camelCase 직렬화 베이스
│           │   ├── feed.py              # ★ 임시 응답 필드명
│           │   └── tag.py               # ★ 임시 응답 필드명
│           ├── services/
│           │   ├── __init__.py
│           │   ├── feed_service.py      # 피드 조회 (AI 호출 없음)
│           │   ├── tag_service.py       # 관심 태그
│           │   ├── curation_service.py  # 큐레이션 로직 (실행기 비의존)
│           │   └── retention_service.py # 보관 정책 로직 (실행기 비의존)
│           ├── routers/
│           │   ├── __init__.py
│           │   ├── feed_router.py
│           │   └── tag_router.py        # tag_router + my_tag_router 2개 export
│           └── tests/
│               ├── __init__.py
│               ├── conftest.py          # 시드 기사/요약 픽스처
│               ├── test_feed_service.py
│               └── test_curation_service.py
└── docs/
    ├── FILE_PLACEMENT_C.md              # 이 문서
    └── api-contracts/_draft/
        └── feed-provisional-api.md      # ★ 임시 API 이름 ↔ D 명세 대조표
```

★ 표시 = D의 계약 확정 시 수정 대상 (총 6개 파일).

---

## 3. 소유권 확인 (CLAUDE.md §3 대조)

| 배치 경로 | 소유 | 상태 |
|---|---|---|
| `backend/app/modules/auth/*` | C | 신규, 단독 수정 가능 |
| `backend/app/modules/feed/*` | C | 신규, 단독 수정 가능 |
| `backend/app/batch/curate.py` | C | 신규, 파일 단위 소유 |
| `backend/app/batch/retention.py` | C | 신규, 파일 단위 소유 |
| `docs/api-contracts/_draft/*` | C 초안 | 계약서 아님. 확정 계약은 D가 `_draft` 밖에 작성 |
| `docs/FILE_PLACEMENT_C.md` | C | 인수인계용 |

`newscollect/`(A), `modules/ai/`, `batch/summarize.py`·`translate.py`(B), `frontend/`(D)에는 **파일을 하나도 넣지 않았다.**

---

## 4. 직접 넣지 않은 것 — 배치 후 별도 처리 필요

전부 **공용 영역**이다. 고치되 무엇을 왜 바꿨는지 팀에 알린다 (CLAUDE.md §5 충돌 방지 규칙 1).

### (1) `backend/app/main.py` — 라우터 등록

```python
from app.modules.auth.routers.auth_router import router as auth_router
from app.modules.feed.routers.feed_router import router as feed_router
from app.modules.feed.routers.tag_router import my_tag_router, tag_router

app.include_router(auth_router)
app.include_router(feed_router)
app.include_router(tag_router)
app.include_router(my_tag_router)
```

### (2) `requirements.txt` — 의존성 2개

```
passlib[bcrypt]
email-validator
```
(한 줄 추가도 자주 겹치므로 rebase 후 즉시 머지 — CLAUDE.md §5-6)

### (3) 공용 모듈 이름 확인 — 없으면 import 에러

| import 경로 | 필요한 것 |
|---|---|
| `app.db.base` | `Base` |
| `app.db.session` | `get_db` |
| `app.core.redis` | `get_redis` |
| `app.common.exceptions` | `NotFoundError`, `ConflictError`, `UnauthorizedError` |
| `app.common.batch_log` | `start_job`, `finish_job`, `log_error` |

0주차 스켈레톤에 다른 이름으로 있으면 **C 코드의 import를 그쪽에 맞춘다.** 아예 없으면 공용 PR로 추가.

### (4) Alembic revision

만들지 않았다. `tags` / `user_tags` / `bookmarks` 등이 `docs/db/schema.sql` V1.1에 없으면 C 창구로 스키마 변경 절차를 밟은 뒤 revision을 생성한다.

---

## 5. 배치 후 확인 순서

```bash
cd backend
pip install -r requirements.txt

# 1) import 경로가 맞는지
python -c "import app.modules.feed.routers.feed_router"

# 2) 모듈 테스트 (C 소유 범위만)
pytest app/modules/auth/tests app/modules/feed/tests -v

# 3) 서버 기동 후 문서 확인 (main.py 등록 이후)
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

테스트가 import 에러로 깨지면 §4-(3)의 공용 모듈 이름부터 맞춘다. DB/Redis 없이 돌아가도록 되어 있으므로 컨테이너를 띄울 필요는 없다.

---

## 6. 파일별 "언제 여는지" 빠른 표

| 상황 | 열 파일 |
|---|---|
| D 계약이 확정돼 API 경로를 맞춘다 | `modules/{auth,feed}/api_paths.py` |
| 응답 필드명을 계약에 맞춘다 | `modules/auth/schemas/auth.py`, `modules/feed/schemas/{feed,tag}.py` |
| camelCase ↔ snake_case를 바꾼다 | `modules/{auth,feed}/schemas/base.py` |
| 태그 매칭 규칙을 바꾼다 | `modules/feed/services/curation_service.py` (`_matches`) |
| 보관 기간을 바꾼다 | `modules/feed/services/retention_service.py` (설정 외부화 대상) |
| 세션 TTL·키를 바꾼다 | `modules/auth/services/session_service.py` |
| 배치 트리거를 붙인다 (기술 확정 후) | `batch/curate.py`·`retention.py`의 `run()`을 **호출만** 한다. 이 파일에 데코레이터를 붙이지 않는다 |
