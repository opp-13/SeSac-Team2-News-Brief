import { apiFetch, ApiError } from './client'
import { fetchTags, toTagIds, type Tag } from './tags'

// 백엔드 UserResponse (backend/app/modules/auth/schemas/auth.py).
interface BackendUser {
  id: number
  email: string
  nickname: string
  /** 'USER' | 'ADMIN' — schema.sql users.role */
  role: string
  preferredLanguage: string
  createdAt: string
}

interface BackendLoginResponse {
  user: BackendUser
  /** 쿠키로도 오므로 프런트는 쓰지 않는다. 백엔드가 아직 바디에도 담아 보낸다. */
  sessionId: string
}

/**
 * 화면이 쓰는 세션 뷰 모델.
 *
 * 백엔드는 리소스를 그대로 준다(`/auth/me` = 사용자, `/me/tags` = 관심 태그).
 * 화면이 필요한 건 "로그인했나 / 관리자인가 / 관심 태그가 뭔가"라서, 두 응답을 여기서
 * 합쳐 하나의 뷰 모델로 만든다. api 레이어가 존재하는 이유가 이 변환이다
 * (frontend/CLAUDE.md §2 "API 호출은 api/{module} 레이어를 경유").
 */
export interface Session {
  isLoggedIn: boolean
  isAdmin: boolean
  userTags: string[]
  email: string | null
  nickname: string | null
}

const GUEST_SESSION: Session = {
  isLoggedIn: false,
  isAdmin: false,
  userTags: [],
  email: null,
  nickname: null,
}

function toSession(user: BackendUser, tags: Tag[]): Session {
  return {
    isLoggedIn: true,
    isAdmin: user.role === 'ADMIN',
    userTags: tags.map((tag) => tag.name),
    email: user.email,
    nickname: user.nickname,
  }
}

/** 관심 태그 조회. 실패해도 세션 자체를 무효로 만들지 않는다(태그가 없는 것과 같게 처리). */
async function fetchMyTagsSafely(): Promise<Tag[]> {
  try {
    return await apiFetch<Tag[]>('/me/tags')
  } catch (err) {
    console.warn('[auth] 관심 태그를 불러오지 못했습니다. 빈 목록으로 진행합니다.', err)
    return []
  }
}

// GET /auth/me. 401은 인증 실패가 아니라 "비로그인"이라는 정상 상태다.
// 그대로 throw하면 useQuery가 isError로 떨어져 ErrorState가 뜨는데, 비로그인은
// 오류가 아니므로 여기서 흡수해 게스트 세션으로 변환한다.
// (네트워크/서버 오류 등 401이 아닌 실패는 그대로 던져 실제 에러로 다룬다.)
export async function fetchMe(): Promise<Session> {
  let user: BackendUser
  try {
    user = await apiFetch<BackendUser>('/auth/me')
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return GUEST_SESSION
    }
    throw err
  }
  return toSession(user, await fetchMyTagsSafely())
}

interface LoginInput {
  email: string
  password: string
}

export async function login(input: LoginInput): Promise<Session> {
  const { user } = await apiFetch<BackendLoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  // 세션 쿠키가 붙은 뒤여야 관심 태그를 읽을 수 있다.
  return toSession(user, await fetchMyTagsSafely())
}

export function logout(): Promise<null> {
  return apiFetch<null>('/auth/logout', { method: 'POST' })
}

interface SignupInput {
  email: string
  password: string
  nickname: string
  userTags: string[]
}

/**
 * 회원가입.
 *
 * **백엔드 `POST /auth/signup`은 세션을 만들지 않는다** (사용자만 생성하고 쿠키를 주지
 * 않는다). 화면은 가입 직후 로그인 상태를 기대하므로 여기서 로그인까지 이어서 호출한다.
 * 온보딩에서 고른 관심 태그도 가입 API가 받지 않아 로그인 후 별도로 저장한다.
 *
 * 호출이 3번으로 늘어나는 건 계약 정합 전의 임시 형태다. 백엔드가 가입 시 세션 발급과
 * 관심 태그를 함께 처리하면 한 번으로 줄어든다 — C와 협의할 항목.
 */
export async function signup(input: SignupInput): Promise<Session> {
  await apiFetch<BackendUser>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      nickname: input.nickname,
      preferredLanguage: 'ko',
    }),
  })

  const session = await login({ email: input.email, password: input.password })

  if (input.userTags.length === 0) return session
  const userTags = await saveUserTags(input.userTags)
  return { ...session, userTags }
}

/**
 * 관심 태그 저장 (SettingsPage · 회원가입 온보딩).
 *
 * 프런트는 이름으로 다루고 백엔드 `PUT /me/tags`는 id를 받으므로, 전체 태그를 읽어
 * 이름→id로 바꿔 보낸다. 응답으로 온 태그 이름을 그대로 돌려줘, 서버가 실제로 저장한
 * 값과 화면이 어긋나지 않게 한다(입력값을 그대로 되돌려주지 않는다).
 */
export async function saveUserTags(tags: string[]): Promise<string[]> {
  const allTags = await fetchTags()
  const saved = await apiFetch<Tag[]>('/me/tags', {
    method: 'PUT',
    body: JSON.stringify({ tagIds: toTagIds(tags, allTags) }),
  })
  return saved.map((tag) => tag.name)
}
