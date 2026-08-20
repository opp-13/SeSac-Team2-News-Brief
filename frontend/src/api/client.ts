// 루트 CLAUDE.md §7 / frontend/CLAUDE.md §6 공통 규약: 모든 API 호출은 이 레이어를
// 경유한다(컴포넌트·훅에서 직접 fetch 금지). BASE=/api/v1, credentials:'include'
// (Redis 세션 쿠키), 응답 봉투는 { success:true, data } | { success:false, error }.
const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export interface ApiSuccess<T> {
  success: true
  data: T
}

export interface ApiFailure {
  success: false
  error: { code: string; message: string }
}

export class ApiError extends Error {
  status: number
  code?: string

  constructor(status: number, message: string, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })

  // 봉투가 아닌 응답도 온다 — 백엔드가 죽어 프록시가 502를 내거나, 경로가 프런트
  // 라우터로 흘러 index.html이 돌아오는 경우다. 그때 res.json()은 SyntaxError를
  // 던지는데, 그대로 새어 나가면 화면에 "Unexpected token '<'" 같은 메시지가 뜬다.
  let body: ApiSuccess<T> | ApiFailure
  try {
    body = (await res.json()) as ApiSuccess<T> | ApiFailure
  } catch {
    throw new ApiError(
      res.status,
      res.ok
        ? '서버 응답을 해석할 수 없습니다.'
        : '서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해주세요.',
      'INVALID_RESPONSE',
    )
  }

  if (!body?.success) {
    const error = (body as ApiFailure)?.error
    throw new ApiError(res.status, error?.message ?? '요청이 실패했습니다.', error?.code)
  }
  // success:true인데 HTTP 상태가 실패인 경우는 계약 위반이지만 방어적으로 처리한다.
  if (!res.ok) {
    throw new ApiError(res.status, '요청이 실패했습니다.')
  }

  return body.data
}
