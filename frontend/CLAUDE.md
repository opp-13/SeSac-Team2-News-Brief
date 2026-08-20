# frontend/CLAUDE.md

> 이 파일은 `frontend/` 디렉토리 전용 지침이다. 루트 `/CLAUDE.md`(팀 전체 규약)를 **상속하며 덮어쓰지 않는다.**
> 두 문서가 충돌하면 §0의 결정 표를 따르고, 표에 없는 충돌은 코드를 쓰기 전에 사용자에게 먼저 알린다.

담당: **D (신현상)** — 프론트엔드 전담
소유 범위: `frontend/src/**` (단, §1의 공용 영역은 조건부)

---

## 0. 시작 전 확인 — 미해결 충돌

**아래 항목이 미해결인 동안에는 해당 영역 코드를 확정하지 말 것.** 임의로 한쪽을 고르지 말고 사용자에게 물어본다.

### 0.1 디자인 토큰 충돌 `[해결 필요 — 최우선]`

루트 `CLAUDE.md` §7과 `docs/design_plan.md`의 컬러가 서로 다르다.

| 역할 | 루트 CLAUDE.md §7 | design_plan.md `[확정]` |
|---|---|---|
| Primary | `#1F3A5F` (딥네이비) | `#0F172A` (slate-900) |
| 강조/액센트 | `#C2410C` (orange-700) | `#155E75` (cyan-800) |
| 배경 | `#FAFAF8` (웜 그레이) | `#F8FAFC` (slate-50) |
| 서페이스 | `#EFEDE7` (베이지) | `#FFFFFF` |

**임시 운영 규칙**: 프론트엔드 구현은 `design_plan.md` 값을 따른다. 피그마 산출물이 이미 이 값으로 구현되어 있고, 루트 §7은 디자인 확정 이전에 작성된 값이기 때문이다.

**단, 이건 팀 합의 사항이다.** 루트 §7은 "전 모듈 공통"으로 선언돼 있으므로 D가 단독으로 바꿀 수 없다. 다음 순서로 처리한다.

1. 팀에 디자인 확정본 공유 → 루트 §7 갱신 PR
2. 승인 전까지 `theme.ts`에 `design_plan.md` 값을 넣고 파일 상단에 미확정 주석을 남긴다
3. 승인 후 주석 제거

**Claude는 이 두 팔레트를 섞지 않는다.** `#C2410C`와 `#155E75`가 한 화면에 같이 나오면 잘못된 것이다.

### 0.2 그 외 미해결

| 항목 | 상태 | 처리 |
|---|---|---|
| **북마크** | 루트 §3에서 D 담당으로 명시. `feed_items.is_bookmarked` 컬럼 존재. 그런데 `design_plan.md` §6.3은 "공유·스크랩 넣지 않는다"로 제외 | 디자인이 없으므로 **구현하지 않는다.** 필요하면 디자인 먼저 요청 |
| **번역 UI** | `design_plan.md`는 "담당자 부재로 범위 제외". 스키마·API에는 존재 | 화면을 만들지 않는다. 상세 모달 요약 블록 위에 **자리만 비워둔다** |
| **비로그인 피드 접근** | 백엔드 확인 대기 | 두 경우 모두 동작하도록 만든다 (`design_plan.md` §7 표) |
| **자유 키워드 입력** | 백엔드 확인 대기 | 설정 화면은 **선택형만** 먼저 구현 |
| **요약 3종 저장 여부** | B·D 협의 미결 | 프론트는 `summaryType` 파라미터를 보내는 구조로 만들되, 3종이 항상 온다고 가정하지 않는다 |
| **다중 프로바이더** | **확정됨** — 스키마 V2가 `model_id`를 `provider` + `model_name`으로 분리(루트 CLAUDE.md §8-10). 프로토타입이 이미 전제하던 구조다 | 관리자 화면 문구·라벨은 "LLM"으로 쓴다. 후속: `types/admin.ts`의 `provider: string`을 스키마 값 유니온으로 좁히고, `theme.ts`의 `colors.provider` 키를 스키마 값에 맞춘다(`claude` → `anthropic`, `gemini` → `google`). **키 이름 변경이지 디자인 값 변경이 아니다** |

---

## 1. 소유 범위와 공용 영역

루트 §3에서 D의 소유는 `frontend/src/**`이되, 아래는 **공용(합의 필요)** 로 분류돼 있다.

```
frontend/src/routes/          ← 공용
frontend/src/constants/       ← 공용 (theme.ts 포함)
frontend/src/components/common/ ← 공용
frontend/src/api/client.ts    ← 공용
frontend/src/types/common/    ← 공용
```

**현실적 운영**: 프론트 담당이 D 한 명이므로 실제로 이 파일들을 쓰는 사람도 D다. 다만 이 영역을 수정할 때는

- 변경 이유와 영향 범위를 팀에 알린다 (별도 PR로 분리할 필요는 없다)
- `api/client.ts`, `types/common`은 백엔드(C)와 계약이 걸린 파일이므로 C에게 리뷰를 요청한다

**Claude는 `frontend/` 밖의 파일을 수정하지 않는다.** `backend/`, `docs/db/`, `infra/`가 필요하면 사용자에게 알린다.

예외: `docs/api-contracts/*.md`는 **읽기 전용으로 참조**한다. 계약에 없는 응답 필드를 발견하면 코드로 우회하지 말고 사용자에게 보고한다.

---

## 2. 기술 스택

루트 §7이 지정한 것 — **임의로 바꾸지 않는다.**

| 항목 | 지정 | 비고 |
|---|---|---|
| 프레임워크 | React + TypeScript | 함수형 컴포넌트만 |
| 서버 상태 | **TanStack Query** | 필수. `useEffect` + `fetch` 직접 조합 금지 |
| 클라이언트 상태 | store (라이브러리 미지정) | Zustand 권장하나 팀 확인 필요 |
| API 호출 | `api/{module}` 레이어 경유 | 컴포넌트에서 직접 `fetch` 금지 |
| 스타일 | Tailwind CSS | 색상은 `constants/theme.ts` 토큰만 |
| 빌드 | Vite | |
| 서빙 | nginx (리버스 프록시 `/api`) | |

**라우터는 루트 문서에 명시되지 않았다.** `react-router-dom`을 쓸 것이고, 처음 설치할 때 사용자에게 확인받는다.

### 피그마 산출물과의 차이 — 그대로 쓰면 안 되는 부분

`design_plan.md`와 함께 받은 피그마 Make 코드는 **프로토타입이다.** 아래는 반드시 교체한다.

| 피그마 코드 | 이 프로젝트 | 이유 |
|---|---|---|
| `window.location.hash` 라우팅 | `react-router-dom` | 해시 라우팅은 SSR·SEO·nginx 설정과 안 맞음 |
| `useState` + `setTimeout` 목 데이터 | TanStack Query + MSW | 루트 §7 규약 |
| `src/data/mockData.ts` | MSW 핸들러 | 실제 API 전환 시 컴포넌트 수정 불필요 |
| `props`로 `isLoggedIn` 전달 | store 또는 `useAuth` 훅 | prop drilling 제거 |
| 컴포넌트 내부 하드코딩 색상 | `constants/theme.ts` | 토큰 일원화 |
| named export (`export function`) | **default export** | 루트 AGENTS.md 규약 |

**단, JSX 구조와 Tailwind 클래스는 최대한 살린다.** 디자인 구현은 이미 끝나 있으므로 다시 그리지 않는다.

---

## 3. 디렉토리 구조

루트 §4가 정한 구조. **폴더는 kebab-case, 컴포넌트 파일은 PascalCase.**

```
frontend/src/
├── app/              # App.tsx, providers (QueryClient, Router)
├── routes/           # 라우트 정의, ProtectedRoute       [공용]
├── pages/
│   ├── feed/         # NewsFeedPage
│   ├── auth/         # LoginPage, SignupPage
│   ├── admin/        # PipelinePage, LLMUsagePage, RetentionPage
│   └── common/       # NotFoundPage, SettingsPage
├── components/
│   ├── feed/         # ArticleRow, ArticleModal, FilterChips
│   ├── auth/         # 로그인 폼 요소
│   ├── admin/        # StatCard, StageProgress, ErrorDrawer
│   └── common/       # Button, Badge, Chip, Skeleton, EmptyState  [공용]
├── api/
│   ├── client.ts     # fetch 래퍼, credentials: 'include'          [공용]
│   ├── feed.ts
│   ├── auth.ts
│   └── admin.ts
├── hooks/            # useAuth, useInfiniteFeed 등
├── store/            # 클라이언트 상태만
├── types/
│   ├── common/       # API 공통 응답 타입                          [공용]
│   ├── feed.ts
│   └── admin.ts
├── constants/        # theme.ts, routes.ts                        [공용]
├── utils/            # 날짜 포맷, 상대시간 변환
└── mocks/            # MSW 핸들러 (실제 API 연동 후에도 유지)
```

**피그마 코드 이관 매핑**

```
src/pages/NewsFeedPage.tsx        → src/pages/feed/NewsFeedPage.tsx
src/pages/LoginPage.tsx           → src/pages/auth/LoginPage.tsx
src/pages/SignupPage.tsx          → src/pages/auth/SignupPage.tsx
src/pages/SettingsPage.tsx        → src/pages/common/SettingsPage.tsx
src/pages/NotFoundPage.tsx        → src/pages/common/NotFoundPage.tsx
src/pages/admin/*.tsx             → src/pages/admin/*.tsx (그대로)
src/components/ArticleModal.tsx   → src/components/feed/ArticleModal.tsx
src/components/Header.tsx         → src/components/common/Header.tsx
src/components/NavRail.tsx        → src/components/common/NavRail.tsx
src/types.ts                      → src/types/{feed,admin}.ts 로 분할
src/data/mockData.ts              → src/mocks/handlers.ts 로 전환
```

---

## 4. 디자인 규칙 (design_plan.md 요약)

전문은 `docs/design_plan.md`. **아래는 위반 시 리뷰 반려 대상이다.**

### 절대 규칙

- **썸네일 이미지 넣지 않는다.** 텍스트 전용 서비스다.
- **드롭섀도우 금지.** 카드 구분은 `1px #E2E8F0` 테두리로만.
- **그라디언트 금지.**
- **상단 고정 영역은 최대 2단, 합계 120px 이하.**
- **한 화면에 Primary 버튼은 하나만.**
- **12px 미만 폰트 금지.** 굵기는 400/500/600만.
- **간격은 4/8/12/16/24/32/48px만.**
- 액센트는 시안 하나로 버틴다. **색을 추가하지 않는다.**
- 빨강·초록은 상태 신호 전용. 브랜드·장식에 쓰지 않는다.
- 관리자 화면에서 앰버(`#F59E0B`) 사용 금지 (부분 실패 노랑과 혼동).
- 아이콘만 있고 라벨 없는 버튼 금지.

### 기사 목록 — 카드가 아니라 "구분선 목록"

떠 있는 카드를 나열하지 않는다. 흰 컨테이너 하나 안에 행이 쌓이고 행 사이만 1px 구분선.

- 행 높이 **100~120px** 목표. 초과하지 않는다.
- 구성: 메타 행(출처 뱃지 + 상대시간) → 헤드라인 2줄 말줄임 → 태그 칩 최대 2개
- **요약문은 목록에 넣지 않는다.** 상세에서만 본다.
- 마지막 행 아래 구분선 없음

### AI 요약 블록 — 시그니처 요소

좌측 2px 세로선 `#155E75` + 12px 간격 + 요약문. 위에 `AI 요약` 라벨(`#CFFAFE` 배경).

**원문 발췌에 이 세로선을 쓰지 않는다.** "기계가 쓴 문장"이라는 신호다.

### 상세는 모달 (페이지 아님)

- URL은 `/articles/:id`로 바뀌지만 **목록 위에 겹친다**
- react-router의 `background location` 패턴을 쓴다
- 데스크톱: 중앙 모달 640px / 모바일: 바텀시트
- 필수 동작: ESC 닫기, 오버레이 클릭 닫기, 포커스 트랩, 닫으면 원래 행으로 포커스 복귀, 배경 스크롤 잠금
- 직접 URL 진입 시에도 목록 위 모달로 보여야 한다 (링크 공유·뒤로가기 정상 동작)
- 좌우 이전/다음 기사 이동 버튼

### 상태 화면 4종은 항상 함께 만든다

목록이 있는 모든 화면에 **로딩(스켈레톤) / 비어있음 / 오류 / 끝 도달**을 함께 구현한다. 기본 상태만 만들고 끝내지 않는다.

- 비어있음에 "데이터가 없습니다"라고만 쓰지 않는다. 다음 행동을 제시한다.
- 로딩은 스피너가 아니라 **스켈레톤 블록 3개**.

---

## 5. 화면 목록

| 라우트 | 화면 | 우선순위 |
|---|---|---|
| `/` | 뉴스 목록 (로그인 여부로 분기) | **최상 — 작업량 30%** |
| `/articles/:id` | 상세 **모달** (페이지 아님) | 상 |
| `/login` | 로그인 | 중 |
| `/signup` | 회원가입 (2단계: 계정 → 관심 태그) | 중 |
| `/settings` | 관심 태그 설정 | 중 |
| `/admin/pipeline` | 배치 이력 + 오류 사이드 드로어(480px) | 중 |
| `/admin/llm-usage` | 요약 카드 4 + 차트 3 | 중 |
| `/admin/retention` | 보관 정책 폼 | 하 |
| `*` | 404 | 하 |

**`/feed`는 만들지 않는다.** `/`로 통합했다.

**검색 화면(`/search`)은 만들지 않는다.** 대신 헤더 중앙 입력창에서 검색하고, 결과는 `/?q=`
쿼리 파라미터로 `/` 목록을 필터링해 보여준다. 검색어의 진실은 URL이며(공유·뒤로가기 정상 동작),
컴포넌트 로컬 상태나 store에 두지 않는다.

> 2026-08-20 변경. 원래 규칙은 "헤더에 아이콘만 둔다"였고 `design_plan.md`에는 검색 UI 디자인이
> 없다. 사용자 요청으로 실제 동작하는 입력창을 넣었으므로 **`docs/design_plan.md`에도 이 결정을
> 기록해야 한다**(현재 미반영 — 디자인 문서와 구현이 갈라진 상태). 또한 서버 검색 API가 없어
> 지금은 `hooks/useFeed.ts`가 목업 배열을 클라이언트에서 거른다. 커서 페이지네이션이 붙으면
> 받아온 페이지 안에서만 검색되는 문제가 생기므로, `GET /feed?q=` 계약이 필요하다.

### `/` 의 두 가지 모드

| | 비로그인 | 로그인 |
|---|---|---|
| 헤딩 | `최신 뉴스` | `관심사 기반 뉴스` |
| 필터 칩 | 카테고리 | 사용자 관심 태그 + `전체` |
| 행의 태그 칩 | 표시 안 함 | 매칭 태그 최대 2개 |
| 상단 배너 | 로그인 유도 1회 | 없음 |

배너를 스크롤 중간에 끼워 넣지 않는다.

---

## 6. API 연동 규칙

### 계약이 먼저다

- 새 API를 쓰기 전에 `docs/api-contracts/{feed,auth,admin}.md`를 확인한다
- **계약에 없는 응답 필드를 가정하지 않는다.** 필요하면 계약 PR을 먼저 올린다
- 계약과 구현이 다르면 코드가 아니라 계약을 기준으로 하고, 사용자에게 보고한다

### 공통 규약

```ts
// api/client.ts
const BASE = '/api/v1'
// 모든 요청에 credentials: 'include' (Redis 세션 쿠키)
// 응답: { success: true, data } | { success: false, error: { code, message } }
```

- 페이지네이션은 **커서 기반** (`cursor` / `nextCursor` / `hasNext`)
- 시각은 ISO 8601 UTC로 받고, KST 변환은 `utils/date.ts`에서 처리
- `401` → 로그인 페이지로, `403` → 권한 없음 표시

### 세션 복원

앱 진입 시 `GET /api/v1/auth/me`로 로그인 상태를 복원한다. **이 API가 없으면 새로고침마다 로그인이 풀린 것처럼 보인다.** 계약에 없으면 사용자에게 알린다.

### MSW 우선

백엔드가 준비되기 전까지 **MSW 핸들러로 개발한다.**

- 핸들러는 `src/mocks/handlers.ts`
- 응답 형태는 계약 문서와 **정확히 일치**시킨다. 여기서 어긋나면 나중에 전부 고쳐야 한다
- 실제 API 연동 후에도 MSW는 지우지 않는다 (테스트·오프라인 개발용)

---

## 7. 코딩 컨벤션

- 함수형 컴포넌트 + TypeScript. 페이지 컴포넌트명은 `XxxPage`
- **default export** 사용
- 색상·폰트는 `constants/theme.ts` 토큰만. Tailwind 임의 색상 클래스 금지
- 서버 상태는 TanStack Query, 클라이언트 상태만 store
- API 호출은 `api/{module}` 경유. 컴포넌트에서 직접 `fetch` 금지
- 폴더 kebab-case, 컴포넌트 파일 PascalCase
- 문자열에 아포스트로피가 있으면 큰따옴표 사용
- `any` 금지. 타입을 모르면 계약 문서를 확인한다

### 접근성 (모달·드로어에서 특히)

- 포커스 트랩, ESC 닫기, 포커스 복귀는 **선택이 아니라 필수**
- 상태 뱃지는 색상만으로 구분하지 않는다. 텍스트를 함께 넣는다
- 관리자 차트의 프로바이더 구분은 색 + **선 패턴(실선/점선)** 을 같이 쓴다

---

## 8. Git 규칙

- 브랜치: `feature/web/{작업명}` (루트 §5는 `feature/{module}/{task}` 형식)
- `main` 직접 push 금지. **기능 브랜치에서 `main`으로 PR** (`develop` 통합 브랜치는 두지 않는다)
- 머지 조건: 리뷰 1인 승인 + CI 통과. `main`이 배포 기준이므로 CI 실패 상태로 머지하지 않는다
- 머지 후 기능 브랜치 삭제
- 커밋: `<type>(<module>): <description>` — 모듈은 `web`
  - 예: `feat(web): 기사 목록 무한스크롤 구현`
- PR은 300줄 이내 목표
- 공용 영역 변경은 기능 PR과 분리

---

## 9. 작업 순서

루트 §3의 의존 순서상 **D는 C의 API를 기다리지 않고 MSW로 병행 진행한다.**

1. **프로젝트 초기화** — Vite + React + TS, Tailwind, react-router, TanStack Query, MSW 설치
2. **`constants/theme.ts`** — §0.1 결정 반영, 디자인 토큰 정의
2.5. **라우터 + 레이아웃 구성** (`routes/`, `Layout`, `Header`, `NavRail`)
   > **이유**: 페이지 컴포넌트를 먼저 만들고 라우터를 나중으로 미루면, 그 페이지를
   > 실제로 마운트해서 확인할 방법이 없다. `App.tsx`가 라우트를 하나도 정의하지 않은
   > 채로 여러 페이지(`NewsFeedPage`, `LoginPage` 등)를 먼저 이식했다가, 화면에
   > 헤더도 없이 통째로 비어 보이는 문제를 겪고 나서야 원인이 "라우터 자체가 없어서
   > 어떤 컴포넌트도 렌더링되지 않는다"는 걸 확인한 적이 있다. 페이지를 하나씩 이식할
   > 때마다 "코드는 맞는데 화면에서 검증이 안 되는" 상태가 계속 길어지는 걸 막기 위해,
   > 라우터·레이아웃 골격을 컴포넌트 이식보다 먼저 끝내둔다.
3. **`components/common/`** — Button, Badge, Chip, Skeleton, EmptyState, ErrorState
4. **`/` 데스크톱** — 구분선 목록 + 필터 칩 + 상태 4종
5. **`/` 모바일** + 비로그인/로그인 두 모드
6. **상세 모달** — 데스크톱 모달 + 모바일 바텀시트 + 라우팅 연동
7. **`/login`, `/signup`, `/settings`**
8. **관리자 3개 화면**
9. **MSW → 실제 API 전환**

**4~6번에 전체 시간의 절반을 쓴다.** 포트폴리오에서 실제로 보여주는 화면이다.

---

## 10. Claude에게 주는 지시사항

### 하지 말 것

- **`frontend/` 밖의 파일을 수정하지 않는다.** 필요하면 먼저 알린다
- **§0의 미해결 항목을 임의로 결정하지 않는다.** 특히 컬러 팔레트
- **계약에 없는 API 필드를 가정하지 않는다.** 추측해서 타입을 만들지 않는다
- **`design_plan.md`의 `[확정]` 값을 바꾸지 않는다.** 더 나아 보여도 그대로 쓴다
- **디자인에 없는 기능을 추가하지 않는다** (북마크, 공유, 번역 UI, 검색 화면, 관련 기사)
- **라이브러리를 임의로 설치하지 않는다.** 먼저 제안하고 확인받는다
- 시크릿·API 키를 코드에 넣지 않는다. `.env.example`에 플레이스홀더만

### 할 것

- 컴포넌트를 만들 때 **상태 4종(로딩/비어있음/오류/끝)을 함께** 만든다
- 새 색상·간격이 필요하면 토큰에 있는지 먼저 확인한다. 없으면 **디자인 문서 위반이므로 사용자에게 묻는다**
- 피그마 코드의 JSX 구조와 Tailwind 클래스는 최대한 재사용한다. 다시 그리지 않는다
- 모달·드로어를 만들면 접근성 요구사항(§7)을 빠짐없이 구현한다
- 작업 후 실제로 렌더링되는지 확인한다. 타입 에러가 있으면 넘어가지 않는다

### 애매하면

**임의로 결정하지 말고 묻는다.** 이 프로젝트는 4인 팀 협업이고, 프론트 단독 결정이 계약·스키마·다른 모듈에 영향을 준다. 특히 API 응답 형태, 컬러, 새 기능 추가는 반드시 확인을 받는다.
