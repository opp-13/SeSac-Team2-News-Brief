// LLM 프로바이더 식별자 ↔ 표시 라벨.
//
// 왜 나누는가: 프로토타입은 'OpenAI' / 'Claude' / 'Gemini' 라는 **표시용 문자열을 데이터 값
// 자체로** 쓰고 있었다. 스키마 V2가 `provider` 컬럼을 도입하면서(`summaries.provider`,
// `ai_invocations.provider`) 서버는 'openai' / 'anthropic' / 'google' 을 내려준다.
// 값은 스키마를 따르고, 사람이 읽는 이름은 여기서 붙인다.
// (docs/api-contracts/admin.md "provider — 스키마 V2에서 해소됨")
//
// 프로바이더를 추가하려면 PROVIDERS 와 LABELS, 그리고 theme.ts 의 colors.provider 를
// 함께 늘린다. 셋이 어긋나면 차트에서 색이 빠지거나 라벨이 식별자로 노출된다.

export const PROVIDERS = ['openai', 'anthropic', 'google'] as const

export type Provider = (typeof PROVIDERS)[number]

const LABELS: Record<Provider, string> = {
  openai: 'OpenAI',
  anthropic: 'Claude',
  google: 'Gemini',
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
  return isKnownProvider(provider) ? LABELS[provider] : provider
}
