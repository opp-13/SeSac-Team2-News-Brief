// LLM 프로바이더 식별자 ↔ 표시 라벨.
//
// 왜 나누는가: 프로토타입은 'OpenAI' / 'Claude' / 'Gemini' 라는 **표시용 문자열을 데이터 값
// 자체로** 쓰고 있었다. 스키마 V2가 `provider` 컬럼을 도입하면서(`summaries.provider`,
// `ai_invocations.provider`) 서버는 'openai' / 'anthropic' / 'google' 을 내려준다.
// 값은 스키마를 따르고, 사람이 읽는 이름은 여기서 붙인다.
// (docs/api-contracts/admin.md "provider — 스키마 V2에서 해소됨")
//
// 라벨만 추가하려면 LABELS 에 한 줄이면 된다. 차트에 고유 색까지 주려면 PROVIDERS 와
// theme.ts 의 colors.provider 를 함께 늘린다 — 색 배정은 디자인 결정이다.

// 차트에 고유 색이 배정된 프로바이더. 색은 design_plan.md §2가 정한다.
export const PROVIDERS = ['openai', 'anthropic', 'google'] as const

export type Provider = (typeof PROVIDERS)[number]

// 라벨은 색과 별개로 둔다. 색 배정은 디자인 결정이지만 라벨은 아니라서, 색이 아직 없는
// 프로바이더도 이름만은 사람이 읽을 수 있게 보여줄 수 있다.
//
// `groq`은 수집 파이프라인이 실제로 쓰는 요약 프로바이더다
// (newscollect/processing/db.py가 summaries.provider='groq'으로 기록한다).
// 차트 색은 아직 배정되지 않아 '기타'(slate-600)로 떨어진다 — 디자인 결정 대기.
const LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Claude',
  google: 'Gemini',
  groq: 'Groq',
}

export function isKnownProvider(value: string): value is Provider {
  return (PROVIDERS as readonly string[]).includes(value)
}

/**
 * 표시용 이름. 스키마의 `provider`는 ENUM이 아니라 VARCHAR(50)이라 서버가 아직 모르는
 * 값을 보낼 수 있다. 그때는 화면을 비우지 말고 원본 값을 그대로 보여준다 —
 * 라벨이 빠지는 것보다 낯선 식별자라도 보이는 편이 낫다.
 */
export function providerLabel(provider: string): string {
  return LABELS[provider] ?? provider
}
