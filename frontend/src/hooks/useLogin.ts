import { useMutation, useQueryClient } from '@tanstack/react-query'
import { login } from '../api/auth'
import { SESSION_QUERY_KEY } from './useSessionQuery'

// frontend/CLAUDE.md §2 규칙2: useState+setTimeout 목업 → TanStack Query(useMutation).
// 세션은 useSessionQuery(['auth','me']) 캐시가 유일한 진실 공급원이므로, 로그인 성공 시
// store 액션이 아니라 이 쿼리 캐시를 갱신한다. 응답을 즉시 반영(setQueryData)하고
// 백그라운드로 재검증(invalidateQueries)해 서버 진실과 다시 맞춘다.
export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: login,
    onSuccess: (session) => {
      queryClient.setQueryData(SESSION_QUERY_KEY, session)
      queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY })
    },
  })
}
