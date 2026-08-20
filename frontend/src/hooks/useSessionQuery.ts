import { useQuery } from '@tanstack/react-query'
import { fetchMe } from '../api/auth'

// useAuth/useLogin/useLogout이 전부 같은 키를 참조해야 캐시가 어긋나지 않는다.
export const SESSION_QUERY_KEY = ['auth', 'me'] as const

// frontend/CLAUDE.md §2: 세션은 서버 상태이므로 TanStack Query가 유일한 진실 공급원이다.
export function useSessionQuery() {
  return useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: fetchMe,
    retry: false,
  })
}
