/**
 * ⚠️ 미확정 — frontend/CLAUDE.md §0.1 참고 (해결 필요 · 최우선)
 *
 * 루트 `/CLAUDE.md` §7과 `docs/design_plan.md` §2의 컬러 값이 서로 다르다.
 *
 *   역할        | 루트 CLAUDE.md §7          | design_plan.md `[확정]`
 *   ----------- | --------------------------- | ------------------------
 *   Primary     | #1F3A5F (딥네이비)          | #0F172A (slate-900)
 *   강조/액센트 | #C2410C (orange-700)        | #155E75 (cyan-800)
 *   배경        | #FAFAF8 (웜 그레이)         | #F8FAFC (slate-50)
 *   서페이스    | #EFEDE7 (베이지)            | #FFFFFF
 *
 * 이 파일은 `design_plan.md` 값을 채택했다 — 피그마 산출물이 이미 이 값으로
 * 구현돼 있고, 루트 §7은 디자인 확정 이전에 작성된 값이기 때문이다.
 * 단, 루트 §7은 "전 모듈 공통"으로 선언돼 있어 프론트가 단독으로 확정할 수
 * 없는 팀 합의 사항이다.
 *
 * 처리 순서:
 *   1. 팀에 디자인 확정본 공유 → 루트 §7 갱신 PR
 *   2. 승인 전까지 이 주석과 아래 design_plan.md 값을 그대로 유지한다
 *   3. 승인 후 이 주석 블록을 제거한다
 *
 * #C2410C(루트 액센트)와 #155E75(design_plan 액센트)를 한 화면에 함께
 * 쓰지 않는다 — 두 팔레트를 섞지 않는다.
 *
 * ---
 * 이 파일은 루트 CLAUDE.md §3 기준 공용 영역이다 (frontend/CLAUDE.md §1).
 * 수정 시 기능 PR과 분리하고, 변경 이유를 PR 본문에 남긴다.
 */

// ─────────────────────────────────────────────────────────
// 컬러 — design_plan.md §2 `[확정]`. 커스텀 컬러 추가 금지.
// ─────────────────────────────────────────────────────────

export const colors = {
  // 코어
  primary: '#0F172A', // slate-900 — 헤드라인, 본문 텍스트, 헤더
  accent: '#155E75', // cyan-800 — CTA 버튼, 링크, AI 요약 라벨
  accentTint: '#CFFAFE', // cyan-100 — 뱃지 배경 (글자는 accent)
  surface: '#FFFFFF', // white — 카드 배경
  surfaceAlt: '#F8FAFC', // slate-50 — 페이지 배경
  border: '#E2E8F0', // slate-200 — 카드 구분선, 입력 필드 테두리
  muted: '#64748B', // slate-500 — 출처명, 날짜, 보조 정보

  // 상태 (뱃지 형태로만 사용)
  status: {
    success: { bg: '#DCFCE7', text: '#166534' }, // green-100 / green-800 — 배치 성공
    partial: { bg: '#FEF9C3', text: '#854D0E' }, // yellow-100 / yellow-800 — 일부 기사 처리 실패
    error: { bg: '#FEE2E2', text: '#991B1B' }, // red-100 / red-800 — 배치 실패, 비용 임계치 초과
    pending: { bg: '#F1F5F9', text: '#334155' }, // slate-100 / slate-700 — 실행 예정
  },

  // 뱃지 등 일반 용도의 중립색. status.pending과 값은 같지만(slate-100/slate-700),
  // status.*는 배치/처리 상태 전용 이름이라 출처 뱃지 같은 일반 UI에는 이 토큰을 쓴다.
  // design_plan.md §2가 새 색값을 금지하므로 값 자체는 재사용, 이름만 분리했다.
  neutral: { bg: '#F1F5F9', text: '#334155' },

  // 프로바이더 구분색 (관리자 차트 전용 — 반드시 선 패턴과 함께 사용)
  provider: {
    openai: '#6D28D9', // violet-700
    claude: '#C2410C', // orange-700
    gemini: '#BE185D', // pink-700
    other: '#475569', // slate-600
  },

  // 특수
  special: {
    // "신규" / "속보" 뱃지 전용. 사용자 화면에서만 사용.
    // 관리자 화면 사용 금지 — status.partial(부분 실패 노랑)과 혼동됨.
    newBadgeDot: '#F59E0B', // amber-500
  },
} as const

// 다크모드는 2차 작업 (design_plan.md §2). 지금은 라이트모드 값만 정의한다.
// 진행 시 accent를 #155E75 → #22D3EE(cyan-400)로 교체 예정
// (#155E75는 어두운 배경에서 시인성이 떨어짐).

// ─────────────────────────────────────────────────────────
// 타이포그래피 — design_plan.md §3 `[제안]` (팀 합의 전, 조정 가능)
// ─────────────────────────────────────────────────────────

export const fontFamily = {
  // Figma에 Pretendard가 없으면 Noto Sans KR로 대체
  sans: "'Pretendard', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
} as const

// 숫자가 많은 관리자 표·차트 축 라벨은 이 옵션을 켜서 자릿수를 정렬한다.
export const numericFontFeature = "'tabular-nums'" as const

/**
 * 행간(lineHeight) 매핑 근거 — design_plan.md §3 "행간: 헤드라인 1.4, 본문 1.6, 뱃지 1.0":
 *   헤드라인류(display/h1/h2/headline) → 1.4
 *   본문류(body/caption)              → 1.6
 *   뱃지류(micro)                     → 1.0
 * 문서가 역할별 행간을 개별 지정하지 않아 위 3개 그룹으로 나눠 적용했다.
 */
export const typeScale = {
  display: { fontSize: '28px', fontWeight: 600, letterSpacing: '-0.02em', lineHeight: 1.4 }, // 페이지 타이틀
  h1: { fontSize: '22px', fontWeight: 600, letterSpacing: '-0.01em', lineHeight: 1.4 }, // 섹션 헤딩
  h2: { fontSize: '18px', fontWeight: 600, letterSpacing: '-0.01em', lineHeight: 1.4 }, // 카드 그룹 헤딩
  headline: { fontSize: '16px', fontWeight: 600, letterSpacing: '-0.01em', lineHeight: 1.4 }, // 기사 카드 제목
  body: { fontSize: '15px', fontWeight: 400, letterSpacing: '0', lineHeight: 1.6 }, // AI 요약 본문
  caption: { fontSize: '13px', fontWeight: 400, letterSpacing: '0', lineHeight: 1.6 }, // 출처, 시간, 보조
  micro: { fontSize: '12px', fontWeight: 500, letterSpacing: '0', lineHeight: 1.0 }, // 뱃지, 칩 라벨
} as const

// 굵기는 이 3가지만 사용 (design_plan.md §3 금지 사항)
export const allowedFontWeights = [400, 500, 600] as const

// 12px 미만 사용 금지 (design_plan.md §3 금지 사항)
export const MIN_FONT_SIZE_PX = 12

// ─────────────────────────────────────────────────────────
// 간격 — design_plan.md §4 `[제안]` (팀 합의 전, 조정 가능)
// ─────────────────────────────────────────────────────────

// 이 7개 값만 사용한다 (design_plan.md §4 금지 사항)
export const spacingScale = [4, 8, 12, 16, 24, 32, 48] as const

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  '2xl': 32,
  '3xl': 48,
} as const

// 카드 내부 여백 (상 하 / 좌 우)
export const cardPadding = {
  desktop: { y: 16, x: 20 },
  mobile: { y: 14, x: 16 },
} as const

// ─────────────────────────────────────────────────────────
// 모서리 · 테두리 — design_plan.md §4 `[제안]` (팀 합의 전, 조정 가능)
// ─────────────────────────────────────────────────────────

export const radius = {
  card: 12,
  control: 8, // 버튼 · 입력 필드
  chip: 6, // 뱃지 · 칩
  avatar: '9999px', // 아바타 원형
} as const

export const border = {
  color: colors.border, // #E2E8F0
  width: {
    default: 1,
    // 강조가 필요하면 색을 바꾸지 말고 두께만 2px로 (design_plan.md §4)
    emphasis: 2,
  },
} as const

// ─────────────────────────────────────────────────────────

const theme = {
  colors,
  fontFamily,
  numericFontFeature,
  typeScale,
  allowedFontWeights,
  spacing,
  spacingScale,
  cardPadding,
  radius,
  border,
} as const

export type Theme = typeof theme

export default theme
