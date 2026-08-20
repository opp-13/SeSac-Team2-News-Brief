import { apiFetch, ApiError } from './client'

export interface Session {
  isLoggedIn: boolean
  isAdmin: boolean
  userTags: string[]
}

const GUEST_SESSION: Session = { isLoggedIn: false, isAdmin: false, userTags: [] }

// docs/api-contracts/auth.md — GET /auth/me. 401은 인증 실패가 아니라 "비로그인"이라는
// 정상 상태다. 그대로 throw하면 useQuery가 isError로 떨어져 ErrorState가 뜨는데,
// 비로그인은 오류가 아니므로 여기서 흡수해 게스트 세션으로 변환한다.
// (네트워크/서버 오류 등 401이 아닌 실패는 그대로 던져 실제 에러로 다룬다.)
export async function fetchMe(): Promise<Session> {
  try {
    return await apiFetch<Session>('/auth/me')
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return GUEST_SESSION
    }
    throw err
  }
}

interface LoginInput {
  email: string
  password: string
}

export function login(input: LoginInput): Promise<Session> {
  return apiFetch<Session>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function logout(): Promise<null> {
  return apiFetch<null>('/auth/logout', { method: 'POST' })
}

interface SignupInput {
  email: string
  password: string
  userTags: string[]
}

// docs/api-contracts/auth.md에 아직 없는 임시 경로(login과 같은 이유). 원본
// SignupPage.tsx는 온보딩 2단계에서 고른 태그를 onLogin()에 넘기지 않고 버렸는데,
// 그러면 2단계 자체가 아무 효과가 없어져서 userTags를 실제로 함께 보내게 했다.
export function signup(input: SignupInput): Promise<Session> {
  return apiFetch<Session>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

// SettingsPage(§2 규칙4의 onSaveTags 대체). docs/api-contracts/auth.md에 아직 이
// 엔드포인트가 없다 — /auth/me 응답에 포함된 userTags를 갱신하는 자리라 같은 리소스
// 취급으로 /auth/me/tags를 임시로 썼다. 계약 확정 전까지는 MSW 목업만 이 경로에 응답한다.
export function saveUserTags(tags: string[]): Promise<string[]> {
  return apiFetch<string[]>('/auth/me/tags', {
    method: 'PATCH',
    body: JSON.stringify({ tags }),
  })
}
