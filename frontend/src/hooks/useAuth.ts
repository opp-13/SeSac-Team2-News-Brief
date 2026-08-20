import { useSessionQuery } from './useSessionQuery'

interface AuthUser {
  userTags: string[]
}

// frontend/CLAUDE.md §2 규칙4: props로 isLoggedIn 전달 → useAuth 훅.
// 세션은 서버 상태라(§2 "서버 상태는 TanStack Query") store가 아니라 useSessionQuery
// (TanStack Query)를 감싸는 파사드로만 노출한다 — store와 쿼리 캐시가 따로 노는
// 이중 진실 공급원을 만들지 않는다.
export function useAuth() {
  const { data, isLoading } = useSessionQuery()

  const isLoggedIn = data?.isLoggedIn ?? false
  const isAdmin = data?.isAdmin ?? false
  const user: AuthUser | null = isLoggedIn ? { userTags: data!.userTags } : null

  return { user, isLoggedIn, isAdmin, isLoading }
}
