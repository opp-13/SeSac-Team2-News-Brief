# Auth API 계약

> **상태: DRAFT — C 승인 대기.** 루트 CLAUDE.md §5 규칙4에 따라 C·D 양측 승인 전까지
> 구현에 착수하지 않는다. 이 문서는 프론트(D)가 이미 구현한 화면이 **실제로 호출하고 있는**
> 요청/응답 형태를 근거로 작성한 초안이다 — 프론트는 현재 이 계약대로 MSW 목업에 붙어
> 동작하며(`frontend/src/mocks/handlers.ts`), 백엔드가 같은 형태로 구현하면 목업만
> 제거하면 된다.
>
> 관련 문서: [feed.md](feed.md) (기사·태그 조회), [admin.md](admin.md) (관리자 집계),
> [meta.md](meta.md) (배포 정보)

## 공통 규약 (루트 CLAUDE.md §6)

- `BASE = /api/v1`
- 모든 요청에 `credentials: 'include'` — Redis 세션 쿠키 (`session:{session_id}`, TTL 30m)
- 응답 봉투: `{ "success": true, "data": ... }` | `{ "success": false, "error": { "code", "message" } }`
- 시각은 **ISO 8601 UTC**로 반환한다. KST 변환·상대시간("12분 전") 계산은 프론트
  (`utils/date.ts`) 책임이므로 서버가 포맷된 문자열을 만들지 않는다.
- 프론트 구현 위치: `frontend/src/api/auth.ts`

## 세션 모델

`users` 테이블(`docs/db/schema.sql`)이 영속 정보를, Redis가 세션 자체를 갖는다.
로그인 성공 시 세션 쿠키를 내려주고, 이후 모든 요청은 그 쿠키로 식별한다.
프론트는 토큰을 직접 저장하지 않는다(localStorage 미사용).

---

## GET /auth/me — 세션 복원

앱 진입 시 로그인 상태를 복원한다. **이 응답 하나로** 로그인 여부·관리자 여부·관심 태그를
모두 얻는다 (Header / NavRail / SettingsPage / NewsFeedPage / AdminRoute 가 공통 참조).

### 요청

바디 없음. 세션 쿠키만으로 판별한다.

### 응답 — 200 (로그인 상태)

```json
{
  "success": true,
  "data": {
    "isLoggedIn": true,
    "isAdmin": false,
    "userTags": ["AI", "개발"]
  }
}
```

| 필드 | 타입 | 출처 |
|---|---|---|
| `isLoggedIn` | boolean | 세션 유효 여부 |
| `isAdmin` | boolean | `users.role = 'ADMIN'` |
| `userTags` | string[] | `user_tags` ⋈ `tags` 의 `tags.name` 목록 |

### 응답 — 401 (비로그인)

```json
{
  "success": false,
  "error": { "code": "UNAUTHENTICATED", "message": "로그인이 필요합니다." }
}
```

### ⚠️ 401 처리 — 이 엔드포인트만 예외

루트 CLAUDE.md §6 공통 규약은 "`401` → 로그인 페이지로"지만, **`/auth/me`에 그 규칙을
그대로 적용하면 비로그인 방문자가 첫 진입부터 `/login`으로 튕기는 무한 루프가 된다.**

프론트는 이 엔드포인트의 401만 예외적으로 흡수해 게스트 세션
(`{ isLoggedIn: false, isAdmin: false, userTags: [] }`)으로 변환한다
(`frontend/src/api/auth.ts` 의 `fetchMe`). 401이 아닌 실패(네트워크·5xx)는 그대로
오류로 다룬다.

즉 **비로그인은 오류가 아니라 정상 상태**이며, 서버는 401로 알려주기만 하면 된다.
서버가 200 + `isLoggedIn: false` 로 바꾸고 싶다면 프론트도 함께 수정해야 하므로
반드시 합의 후 변경한다.

> 이전 초안은 "이 엔드포인트는 401을 쓰지 않는다"고 적었으나, 실제 구현은 401 + 프론트
> 흡수 방식으로 확정됐다. 이 문서가 구현과 일치하는 최신 기준이다.

### 응답 — 5xx

세션 판별 자체가 불가능한 서버 오류:

```json
{ "success": false, "error": { "code": "SESSION_CHECK_FAILED", "message": "..." } }
```

---

## POST /auth/signup — 회원가입

화면: `/signup` (2단계 — 1단계 계정 정보, 2단계 관심 태그 선택).
가입 성공 시 **곧바로 로그인 상태가 되어야 한다** (프론트는 성공 후 `/`로 이동하며
별도 로그인을 요구하지 않는다).

### 요청

```json
{
  "email": "hello@example.com",
  "password": "at-least-8-chars",
  "userTags": ["AI", "개발"]
}
```

| 필드 | 제약 | 비고 |
|---|---|---|
| `email` | 필수, 이메일 형식 | `users.email` UNIQUE (`uk_users_email`) |
| `password` | 필수, **8자 이상** | 프론트에서 `minLength=8` 검증. 서버도 동일 기준으로 재검증할 것 |
| `userTags` | 빈 배열 허용 | 2단계를 건너뛴 사용자는 `[]` |

### 응답 — 201

`GET /auth/me` 의 `data`와 **동일한 형태**를 반환한다 (프론트가 이 응답을 세션 캐시에
그대로 넣는다 — `frontend/src/hooks/useSignup.ts`).

```json
{
  "success": true,
  "data": { "isLoggedIn": true, "isAdmin": false, "userTags": ["AI", "개발"] }
}
```

가입으로는 **관리자가 될 수 없다** (`users.role`은 항상 `'USER'`로 생성).

### 응답 — 400 / 409

| 상황 | code | HTTP |
|---|---|---|
| 이메일·비밀번호 누락 또는 형식 오류 | `INVALID_CREDENTIALS` | 400 |
| 비밀번호 8자 미만 | `PASSWORD_TOO_SHORT` | 400 |
| 이미 존재하는 이메일 | `EMAIL_ALREADY_EXISTS` | 409 |

### ⚠️ 미해결 — `users.nickname`

스키마의 `users.nickname VARCHAR(50) NOT NULL`을 **가입 화면이 수집하지 않는다.**
디자인(`frontend/docs/design_plan.md`)에 닉네임 입력란이 없어서 프론트가 임의로
필드를 추가할 수 없다. 아래 중 하나를 골라야 한다.

1. 서버가 이메일 local-part로 자동 생성 (`hello@example.com` → `hello`) — 화면 변경 없음
2. 가입 폼에 닉네임 입력 추가 — **디자인 변경이므로 디자인 담당 승인 필요**
3. `nickname`을 NULL 허용으로 변경 — **스키마 변경이므로 C 창구 경유**

프론트는 결정 전까지 `nickname`을 보내지 않는다.

---

## POST /auth/login — 로그인

화면: `/login`

### 요청

```json
{ "email": "hello@example.com", "password": "..." }
```

### 응답 — 200

`GET /auth/me` 의 `data`와 동일한 형태. 세션 쿠키를 함께 내려준다.
성공 시 `users.last_login_at`을 갱신할 것.

```json
{
  "success": true,
  "data": { "isLoggedIn": true, "isAdmin": true, "userTags": ["AI", "개발"] }
}
```

### 응답 — 400 / 401

| 상황 | code | HTTP |
|---|---|---|
| 이메일·비밀번호 누락 | `INVALID_CREDENTIALS` | 400 |
| 자격 증명 불일치 | `INVALID_CREDENTIALS` | 401 |
| 탈퇴·휴면 계정 (`users.status != 'ACTIVE'`) | `ACCOUNT_INACTIVE` | 403 |

> 존재하지 않는 이메일과 비밀번호 불일치를 **같은 code로** 응답한다 (계정 존재 여부 노출 방지).

### 현재 목업의 임시 동작 — 실구현 시 제거

MSW 목업은 "이메일에 `admin` 문자열이 포함되면 관리자"로 판정한다
(`frontend/src/mocks/handlers.ts`). 프로토타입 편의 장치이며 **실제 권한 판정은
`users.role`을 따른다.** 목업 제거 시 이 로직도 함께 사라진다.

---

## POST /auth/logout — 로그아웃

### 요청

바디 없음.

### 응답 — 200

```json
{ "success": true, "data": null }
```

서버는 Redis 세션을 삭제하고 세션 쿠키를 만료시킨다.
프론트는 성공 시 세션 쿼리 캐시를 **비운다**(`removeQueries`) — 값을 추측해 넣지 않고,
다음 조회에서 서버가 준 상태(401 → 게스트)를 그대로 받는다.

---

## PATCH /auth/me/tags — 관심 태그 저장

화면: `/settings` (관심 태그 설정)

### 요청

```json
{ "tags": ["AI", "개발", "반도체"] }
```

전달된 목록이 **전체 상태를 대체한다** (부분 추가/삭제가 아닌 전량 치환).
빈 배열은 "관심 태그 없음"으로 유효한 상태다 — 이 경우 피드는 전체 최신 뉴스를 보여준다.

### 응답 — 200

저장 후의 태그 목록을 반환한다. 프론트는 이 값으로 세션 캐시의 `userTags`만 갱신한다
(`frontend/src/hooks/useSaveUserTags.ts`).

```json
{ "success": true, "data": ["AI", "개발", "반도체"] }
```

### 응답 — 401 / 400

| 상황 | code | HTTP |
|---|---|---|
| 비로그인 | `UNAUTHENTICATED` | 401 |
| 존재하지 않는 태그 이름 포함 | `UNKNOWN_TAG` | 400 |

### ⚠️ 미해결 — 태그를 이름으로 주고받는 문제

프론트는 태그를 **이름 문자열**(`"AI"`, `"개발"`)로 보내지만, 스키마는
`user_tags.tag_id → tags.id` 로 참조한다. 서버가 매 요청마다 이름 → id를 해석해야 한다.

현재 프론트의 선택 가능한 태그 목록은 `frontend/src/constants/tags.ts`에 **하드코딩**돼
있고, 스키마의 `tags` 마스터 테이블과 동기화되지 않는다. 태그가 추가/변경되면 즉시 어긋난다.

→ [feed.md](feed.md) 의 `GET /tags` 로 마스터 목록을 받아오도록 전환하는 것을 제안한다.
그 전환 시 이 엔드포인트도 `tags: string[]`(이름) 대신 `tagIds: number[]` 또는
`tags.slug` 기반으로 바꾸는 게 안전하다. **어느 쪽으로 갈지 C와 합의 필요.**

---

## 이 문서 범위 밖

- 비밀번호 재설정·이메일 인증: 요구사항 명세서에 없고 디자인도 없다.
- 회원 탈퇴(`users.status = 'WITHDRAWN'`): 화면 없음.
- `users.preferred_language` / `default_summary_type`: 번역 UI가 범위에서 제외돼
  (frontend/CLAUDE.md §0.2) 이를 변경하는 화면이 없다. 가입 시 스키마 기본값
  (`ko` / `THREE_LINE`)을 그대로 사용한다.

## 열려있는 질문 (C 확인 필요)

1. **`nickname` 처리** — 위 3개 안 중 선택 (가입 구현 전 필수 결정)
2. **태그 식별자** — 이름 vs `tags.id` vs `tags.slug` (위 참고)
3. **세션 TTL 갱신 정책** — Redis `session:{id}` TTL 30m이 요청마다 연장되는지(sliding)
   고정인지. 프론트의 세션 재검증 주기를 여기 맞춘다.
4. **`GET /auth/me` 캐시 가능 여부** — 프론트는 로그인/로그아웃/태그저장 시점에만
   무효화할 계획이다. 서버가 별도 캐시 헤더를 요구하면 알려줄 것.
