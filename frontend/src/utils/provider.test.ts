import { describe, expect, it } from 'vitest'
import { isKnownProvider, providerLabel, PROVIDERS } from './provider'

describe('providerLabel', () => {
  it('스키마 값을 표시용 이름으로 바꾼다', () => {
    expect(providerLabel('openai')).toBe('OpenAI')
    expect(providerLabel('anthropic')).toBe('Claude')
    expect(providerLabel('google')).toBe('Gemini')
  })

  it('차트 색이 없는 프로바이더도 라벨은 보여준다', () => {
    // groq은 수집 파이프라인이 실제로 쓰지만 아직 차트 색이 배정되지 않았다.
    expect(providerLabel('groq')).toBe('Groq')
    expect(isKnownProvider('groq')).toBe(false) // 색 배정 대상은 아니다
  })

  it('모르는 값이 오면 원본을 그대로 보여준다', () => {
    // 스키마의 provider는 ENUM이 아니라 VARCHAR(50)이라 서버가 새 값을 보낼 수 있다.
    // 화면이 비는 것보다 낯선 식별자라도 보이는 편이 낫다.
    expect(providerLabel('mistral')).toBe('mistral')
    expect(providerLabel('')).toBe('')
  })

  it('표시 라벨을 값으로 되먹여도 라벨로 오인하지 않는다', () => {
    // 프로토타입이 데이터로 쓰던 'Claude' 같은 문자열은 이제 유효한 provider 값이 아니다.
    expect(isKnownProvider('Claude')).toBe(false)
    expect(providerLabel('Claude')).toBe('Claude')
  })
})

describe('isKnownProvider', () => {
  it('PROVIDERS에 있는 값만 통과시킨다', () => {
    for (const p of PROVIDERS) {
      expect(isKnownProvider(p)).toBe(true)
    }
    expect(isKnownProvider('bedrock')).toBe(false)
  })
})
