import { useMutation, useQueryClient } from '@tanstack/react-query'
import { signup } from '../api/auth'
import { SESSION_QUERY_KEY } from './useSessionQuery'

// hooks/useLogin.ts와 같은 패턴 — 가입 성공 시 세션 캐시를 즉시 반영(setQueryData)하고
// 백그라운드로 재검증(invalidateQueries)한다.
export function useSignup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: signup,
    onSuccess: (session) => {
      queryClient.setQueryData(SESSION_QUERY_KEY, session)
      queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY })
    },
  })
}
