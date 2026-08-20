# 피그마 Make 산출물 (읽기 전용)

Figma Make가 생성한 디자인 프로토타입 원본입니다.
**디자인 대조용 참조 자료이며, 실행되지 않습니다.**

---

## 규칙

- **이 폴더의 파일은 수정하지 않습니다.**
- 실제 작업은 `frontend/src/` 에서 합니다.
- 이식 방법은 `frontend/CLAUDE.md` §2(교체 항목), §3(경로 매핑) 참고.
- 디자인 스펙 원문은 `frontend/docs/design_plan.md` 참고.

---

## 파일 구성

| 경로 | 줄 수 | 참조 가치 |
|---|---|---|
| `pages/NewsFeedPage.tsx` | 378 | **최상.** 구분선 목록, 필터 칩, 상태 4종 구현 완료 |
| `components/ArticleModal.tsx` | 329 | **최상.** 포커스 트랩, ESC 닫기, 바텀시트 전환 |
| `pages/admin/PipelinePage.tsx` | 234 | 단계별 진행 표시, 오류 사이드 드로어 |
| `pages/admin/LLMUsagePage.tsx` | 188 | Recharts 차트 3종, 요약 카드 4개 |
| `pages/SignupPage.tsx` | 183 | 2단계 회원가입 (계정 → 관심 태그) |
| `pages/admin/RetentionPage.tsx` | 172 | 보관 정책 폼 |
| `components/Header.tsx` | 168 | 데스크톱/모바일 헤더 분기 |
| `App.tsx` | 140 | 레이아웃 셸 구조 (라우팅은 교체 대상) |
| `pages/LoginPage.tsx` | 121 | |
| `pages/SettingsPage.tsx` | 102 | 관심 태그 다중 선택 |
| `components/NavRail.tsx` | 75 | 좌측 아이콘 레일 64px |
| `types.ts` | 62 | 타입 초안 (분할 대상) |
| `pages/NotFoundPage.tsx` | 20 | |
| `data/mockData.ts` | 196 | **재활용 대상.** 한국어 샘플 기사 |
| `index.css` | 35 | 폰트·스크롤바 설정만 발췌 |

---

## 그대로 쓰면 안 되는 것

| 원본 방식 | 교체 대상 | 이유 |
|---|---|---|
| `window.location.hash` 라우팅 | `react-router-dom` | nginx SPA fallback·링크 공유와 안 맞음 |
| `setTimeout` + `useState` 목 데이터 | MSW + TanStack Query | 루트 `CLAUDE.md` §7 규약 |
| `data/mockData.ts` 직접 import | MSW 핸들러 경유 | 실 API 전환 시 컴포넌트 수정 불필요 |
| `props`로 `isLoggedIn` 전달 | store 또는 `useAuth` 훅 | prop drilling 제거 |
| named export (`export function`) | **default export** | 루트 규약 |
| 하드코딩 색상 (`bg-cyan-800` 등) | `constants/theme.ts` 토큰 | 토큰 일원화 |

---

## 살릴 것

- **JSX 구조와 Tailwind 클래스** — 디자인 구현이 끝나 있으므로 다시 그리지 않습니다.
- **`data/mockData.ts`의 샘플 기사** — MSW 응답 데이터로 재활용합니다. 새로 작성하는 것보다 빠릅니다.
- **`index.css`의 폰트·스크롤바 설정** — 해당 블록만 발췌해 실제 `index.css`로 옮깁니다.
- **`ArticleModal.tsx`의 접근성 구현** — 포커스 트랩, ESC 닫기, 포커스 복귀, 배경 스크롤 잠금이 이미 들어 있습니다.

---

## 경로 매핑

```
pages/NewsFeedPage.tsx      → src/pages/feed/NewsFeedPage.tsx
pages/LoginPage.tsx         → src/pages/auth/LoginPage.tsx
pages/SignupPage.tsx        → src/pages/auth/SignupPage.tsx
pages/SettingsPage.tsx      → src/pages/common/SettingsPage.tsx
pages/NotFoundPage.tsx      → src/pages/common/NotFoundPage.tsx
pages/admin/*.tsx           → src/pages/admin/*.tsx
components/ArticleModal.tsx → src/components/feed/ArticleModal.tsx
components/Header.tsx       → src/components/common/Header.tsx
components/NavRail.tsx      → src/components/common/NavRail.tsx
types.ts                    → src/types/{feed,admin}.ts 로 분할
data/mockData.ts            → src/mocks/handlers.ts 로 전환
```

---

## 제외된 파일

아래는 Figma Make 환경 전용이라 가져오지 않았습니다.

`package.json` · `vite.config.ts` · `tsconfig.json` · `index.html` · `main.tsx` · `vite-env.d.ts` · `.figma/` · `.mise.toml` · `pnpm-lock.yaml` · `AGENTS.md` · `CLAUDE.md`

`AGENTS.md`에는 "Vite 개발 서버가 이미 실행 중"처럼 이 프로젝트에서 사실이 아닌 내용이 있고, `CLAUDE.md`는 `frontend/CLAUDE.md`와 이름이 겹칩니다.

---

## 이식 완료 후

전체 화면 이식이 끝나면 **이 폴더를 삭제하고 커밋**합니다.
삭제 커밋이 곧 "디자인 이식 완료" 시점 기록이 됩니다.

```
chore(web): 피그마 참조 폴더 제거 (이식 완료)
```
