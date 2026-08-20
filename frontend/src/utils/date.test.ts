import { describe, expect, it } from 'vitest'
import { toRelativeTime } from './date'

// relativeTime은 서버가 주지 않고 여기서 만든다(docs/api-contracts/feed.md).
// 백엔드가 타임존 표기 없이 UTC를 보내는 경우가 있어 그 해석이 특히 중요하다 —
// Z 없는 문자열을 로컬 시각으로 읽으면 KST에서 9시간 어긋나 "9시간 전"이 된다.
describe('toRelativeTime', () => {
  const now = new Date('2026-08-20T12:00:00Z')

  it('타임존 표기가 없는 UTC 문자열을 UTC로 해석한다', () => {
    // 백엔드 실제 응답 형태: "2026-08-20T11:30:00" (Z 없음)
    expect(toRelativeTime('2026-08-20T11:30:00', now)).toBe('30분 전')
  })

  it('Z가 붙은 문자열도 같게 해석한다', () => {
    expect(toRelativeTime('2026-08-20T11:30:00Z', now)).toBe('30분 전')
  })

  it('오프셋이 붙은 문자열을 해석한다', () => {
    // 20:30 KST = 11:30 UTC
    expect(toRelativeTime('2026-08-20T20:30:00+09:00', now)).toBe('30분 전')
  })

  it('1분 미만은 "방금"', () => {
    expect(toRelativeTime('2026-08-20T11:59:30Z', now)).toBe('방금')
  })

  it('서버 시계가 앞서 있어도 음수를 노출하지 않는다', () => {
    expect(toRelativeTime('2026-08-20T12:05:00Z', now)).toBe('방금')
  })

  it('시간 단위로 넘어간다', () => {
    expect(toRelativeTime('2026-08-20T09:00:00Z', now)).toBe('3시간 전')
  })

  it('하루 전은 "어제"', () => {
    expect(toRelativeTime('2026-08-19T10:00:00Z', now)).toBe('어제')
  })

  it('이틀 이상은 날짜로 표시한다', () => {
    expect(toRelativeTime('2026-08-15T10:00:00Z', now)).toMatch(/^8월 1[45]일$/)
  })

  it('잘못된 값은 빈 문자열', () => {
    expect(toRelativeTime('not-a-date', now)).toBe('')
  })
})
