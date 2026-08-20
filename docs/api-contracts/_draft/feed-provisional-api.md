# [DRAFT] C 구현 임시 API 명세 — D 계약 정합용

> **이 문서는 계약서가 아니다.** API 명세의 기준은 D가 작성하는 `docs/api-contracts/{feed,auth,admin}.md`다.
> C가 구현을 먼저 진행하기 위해 임시로 붙인 이름들을 모아둔 것이며, D의 명세가 확정되면
> **이 문서의 "D 확정값" 칸을 채우고 → 표에 적힌 코드 위치만 수정**하면 정합이 끝난다.
> 명세와 구현이 다르면 명세가 아니라 C의 코드를 고친다.

## 0. 정합 작업이 필요한 파일은 5개뿐이다

| 무엇 | 파일 |
|---|---|
| 경로·프리픽스·쿠키명·페이지 크기 | `backend/app/modules/auth/api_paths.py` |
| 경로·프리픽스·페이지 크기 | `backend/app/modules/feed/api_paths.py` |
| auth 요청/응답 필드명 | `backend/app/modules/auth/schemas/auth.py` |
| feed 응답 필드명 | `backend/app/modules/feed/schemas/feed.py` |
| tag 요청/응답 필드명 | `backend/app/modules/feed/schemas/tag.py` |

라우터·서비스·테스트에는 경로 문자열이 하드코딩되어 있지 않다. 위 5개 파일만 고치면 전 계층이 따라간다.

---

## 1. 엔드포인트 (임시)

### auth — `backend/app/modules/auth/api_paths.py`

| ID | 메서드 | 임시 경로 | 용도 | 상수명 | D 확정값 |
|---|---|---|---|---|---|
| PROV-A00 | — | `/api/v1` | 전역 프리픽스 | `API_PREFIX` | |
| PROV-A01 | POST | `/api/v1/auth/signup` | 회원가입 | `SIGNUP` | |
| PROV-A02 | POST | `/api/v1/auth/login` | 로그인(세션 발급) | `LOGIN` | |
| PROV-A03 | POST | `/api/v1/auth/logout` | 로그아웃(세션 삭제) | `LOGOUT` | |
| PROV-A04 | GET | `/api/v1/auth/me` | 내 정보(마이페이지) | `ME` | |
| PROV-A05 | PATCH | `/api/v1/auth/me/password` | 비밀번호 변경 | `ME_PASSWORD` | |

### tag — `backend/app/modules/feed/api_paths.py`

| ID | 메서드 | 임시 경로 | 용도 | 상수명 | D 확정값 |
|---|---|---|---|---|---|
| PROV-T01 | GET | `/api/v1/tags` | 선택 가능한 전체 태그 | `TAGS_PREFIX` + `TAG_LIST` | |
| PROV-T02 | GET | `/api/v1/me/tags` | 내 관심 태그 조회 | `ME_TAGS_PREFIX` + `MY_TAG_LIST` | |
| PROV-T03 | PUT | `/api/v1/me/tags` | 관심 태그 **전체 교체** | `MY_TAG_REPLACE` | |
| PROV-T04 | DELETE | `/api/v1/me/tags/{tagId}` | 관심 태그 1개 삭제 | `MY_TAG_DELETE` | |

> PROV-T03은 "전체 교체(PUT)" 방식으로 임시 구현했다. 태그 설정 화면이 개별 추가/삭제(POST/DELETE) 방식이면 D 명세에 맞춰 바꾼다.

### feed — `backend/app/modules/feed/api_paths.py`

| ID | 메서드 | 임시 경로 | 용도 | 상수명 | D 확정값 |
|---|---|---|---|---|---|
| PROV-F01 | GET | `/api/v1/feed` | 피드 목록 | `FEED_LIST` | |
| PROV-F02 | GET | `/api/v1/feed/{feedItemId}` | 피드 상세 | `FEED_DETAIL` | |
| PROV-F03 | POST/DELETE | `/api/v1/feed/{feedItemId}/bookmark` | 북마크 추가/해제 | `FEED_BOOKMARK` | |
| PROV-F04 | GET | `/api/v1/me/bookmarks` | 북마크 목록(**미구현**) | `BOOKMARK_LIST` | |

목록 쿼리 파라미터(임시): `cursor`(int, optional), `limit`(1–50, 기본 20), `tagId`(optional)

---

## 2. 응답 필드 (임시)

### 공통 규약

| 항목 | 임시 결정 | 바꾸는 곳 |
|---|---|---|
| 필드 표기 | **camelCase** (`feedItemId`, `publishedAt`) | 각 모듈 `schemas/base.py`의 `alias_generator` 제거하면 snake_case |
| 페이지네이션 | **커서 기반** (`nextCursor`, `hasNext`) | `schemas/feed.py`의 `FeedListResponse` + `feed_service.list_feed` |
| 날짜 | ISO 8601 (UTC) | 스키마 타입 |
| 성공 응답 | 데이터 객체 직접 반환(래핑 없음) | 래핑(`{ "data": ... }`)이 필요하면 스키마에서 처리 |
| 에러 응답 | `app/common/exceptions`의 공용 핸들러에 위임 | 공용 영역 — 고치면 팀에 알린다 |
| 세션 전달 | HttpOnly 쿠키 `nb_session` (+ `Authorization: Bearer` fallback) | `auth/api_paths.py`, `auth/dependencies.py` |
| 204 사용 | 로그아웃·태그 삭제·북마크 | 라우터 `status_code` |

### FeedItemResponse (PROV-F11) — 목록 1건

| 임시 필드 | 타입 | 비고 | D 확정값 |
|---|---|---|---|
| `feedItemId` | int | | |
| `articleId` | int | | |
| `title` | string | | |
| `press` | string \| null | 언론사 | |
| `publishedAt` | datetime | | |
| `language` | string | 노출 언어 | |
| `summary` | string \| **null** | **저장된 요약이 없으면 null.** 조회 시점 생성 안 함 | |
| `summaryType` | string \| null | `ONE_LINE` / `THREE_LINE` / `DETAIL` | |
| `originalUrl` | string | 원문 링크 | |
| `isBookmarked` | bool | | |

### FeedDetailResponse (PROV-F14) — 상세

`feedItemId`, `articleId`, `title`, `press`, `publishedAt`, `language`, `originalUrl`, `isBookmarked`
\+ `oneLineSummary`, `threeLineSummary`, `detailSummary` (각각 없으면 null)

> **D 확인 필요**: 상세 화면이 요약 3종을 모두 쓰는지. 미결 사항 "요약 3종 저장 여부"(B·D 협의)의 결론에 따라 이 응답 구조가 바뀐다. "상세 1건만 저장 + 프런트 절단" 안으로 가면 `detailSummary` 하나만 남는다.

### auth / tag

- `UserResponse` (PROV-A11): `id`, `email`, `nickname`, `preferredLanguage`, `createdAt`
- `LoginResponse` (PROV-A12): `user`, `sessionId` — **쿠키만 쓸 거면 `sessionId` 제거**(PROV-A13)
- `TagResponse` (PROV-T11): `id`, `name`, `category`
- `MyTagsReplaceRequest` (PROV-T12): `{ "tagIds": [1, 2, 3] }`

### 응답 예시 (현재 구현 기준)

```json
GET /api/v1/feed?limit=2
{
  "items": [
    {
      "feedItemId": 12, "articleId": 1,
      "title": "AI 반도체 시장 확대", "press": "테스트일보",
      "publishedAt": "2026-08-19T02:00:00Z", "language": "ko",
      "summary": "번역된 요약 3줄", "summaryType": "THREE_LINE",
      "originalUrl": "https://news.example.com/1",
      "isBookmarked": false
    }
  ],
  "nextCursor": 11,
  "hasNext": true
}
```

---

## 3. D에게 먼저 물어볼 항목

1. **북마크 API를 C가 제공하는 게 맞는지.** CLAUDE.md §3에서 북마크는 D의 화면 기능으로만 적혀 있고 C의 담당 기능 목록에는 없다. 서버 저장이 필요하면 C가 만들지만, `bookmarks` 테이블이 스키마 V1.1에 없으므로 **스키마 변경 절차(C 창구)**가 선행되어야 한다.
2. **세션 전달 방식** — 쿠키 only인지, 토큰을 바디로도 받는지. CORS·도메인 구성과 함께 결정 필요.
3. **페이지네이션 방식** — 커서 vs 페이지 번호. 무한 스크롤이면 커서 유지가 낫다.
4. **요약 없는 기사 처리** — 현재는 `summary: null`로 내려보낸다. 아예 목록에서 제외할지 D 화면 요구에 따라 결정.
5. **태그 설정 화면 방식** — 전체 교체(PUT) vs 개별 토글.
6. **에러 응답 포맷** — 현재는 공용 예외 핸들러에 위임. 프런트가 기대하는 `{code, message}` 형태를 알려주면 맞춘다.

---

## 4. 구현하면서 전제한 것 (확인 필요)

### 공용 모듈 (C 소유 아님 — 고치면 팀에 알린다)

| import 경로 | 용도 |
|---|---|
| `app.db.base.Base` | SQLAlchemy declarative base |
| `app.db.session.get_db` | 세션 의존성 |
| `app.core.redis.get_redis` | Redis 클라이언트 의존성 |
| `app.common.exceptions.{NotFoundError, ConflictError, UnauthorizedError}` | 공통 예외 |
| `app.common.batch_log.{start_job, finish_job, log_error}` | `batch_jobs` / `job_logs` 기록 |

0주차 공용 스켈레톤에 위 항목이 없으면 이름을 맞추거나 공용 PR로 추가해야 한다.

### 스키마 (`docs/db/schema.sql` V1.1과 대조 필요, `[SCHEMA-CHECK]` 주석)

- `tags` / `user_tags` 테이블명·컬럼
- `feed_items`의 `summary_id` / `translation_id` / `matched_tag_id` 존재 여부
- `articles.status`의 "요약 완료" 상태값 (현재 `SUMMARIZED`로 가정)
- `bookmarks` 테이블 (**현재 스키마에 없을 가능성이 높음**)
- 기사↔태그 매핑 테이블 유무 — 없어서 **제목 부분일치**로 임시 매칭 중 (`curation_service._matches`)

### 의존성 추가 필요

- `passlib[bcrypt]` (비밀번호 해시), `email-validator` (Pydantic `EmailStr`)
- `requirements.txt`는 충돌이 잦은 공용 파일이므로 별도 PR로 추가 후 즉시 머지 (CLAUDE.md §5-6)

### 라우터 등록

`backend/app/main.py`에 아래 라우터 등록이 필요하다. **공용 파일이므로 등록했으면 팀에 알린다.**

```python
from app.modules.auth.routers.auth_router import router as auth_router
from app.modules.feed.routers.feed_router import router as feed_router
from app.modules.feed.routers.tag_router import my_tag_router, tag_router
```

### 배치 (`batch/curate.py`, `batch/retention.py`)

스케줄러/큐 라이브러리를 쓰지 않았다. `run(db, ...)` 함수만 있고 트리거는 없다.
기술 확정 후 별도 계층에서 이 함수를 호출하면 된다.
