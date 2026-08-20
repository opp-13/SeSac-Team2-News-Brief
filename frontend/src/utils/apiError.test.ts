import { describe, expect, it } from 'vitest'
import { ApiError } from '../api/client'
import { errorMessage } from './apiError'

const FALLBACK = '네트워크 상태를 확인해주세요.'

describe('errorMessage', () => {
  it('서버가 내려준 메시지를 그대로 쓴다', () => {
    const err = new ApiError(401, '이메일 또는 비밀번호가 올바르지 않습니다.', 'INVALID_CREDENTIALS')
    expect(errorMessage(err, FALLBACK)).toBe('이메일 또는 비밀번호가 올바르지 않습니다.')
  })

  it('서버 메시지가 없는 실패는 fallback으로 바꾼다', () => {
    // fetch가 끊기면 TypeError('Failed to fetch')가 온다. 그대로 보여주면 안 된다.
    expect(errorMessage(new TypeError('Failed to fetch'), FALLBACK)).toBe(FALLBACK)
  })

  it('에러가 없으면 빈 문자열 — 화면에 빈 자리를 만들지 않는다', () => {
    expect(errorMessage(null, FALLBACK)).toBe('')
    expect(errorMessage(undefined, FALLBACK)).toBe('')
  })
})
