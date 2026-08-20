import { ApiError } from '../api/client'

/**
 * 뮤테이션/쿼리 실패를 사용자에게 보여줄 한 문장으로 바꾼다.
 *
 * 서버는 이미 사람이 읽을 한국어 메시지를 내려준다
 * (예: `{"code":"INVALID_CREDENTIALS","message":"이메일 또는 비밀번호가 올바르지 않습니다."}`).
 * 그 메시지를 그대로 쓴다 — 화면마다 코드별 문구를 다시 정의하면 서버와 갈라진다.
 *
 * `ApiError`가 아니면 네트워크·파싱 단계에서 끊긴 것이라 서버 메시지가 없다.
 * 이때 `Failed to fetch` 같은 원문을 그대로 노출하지 않고 fallback 문구로 바꾼다.
 */
export function errorMessage(error: unknown, fallback: string): string {
  if (!error) return ''
  if (error instanceof ApiError) return error.message
  return fallback
}
