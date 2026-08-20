import { useMutation, useQueryClient } from '@tanstack/react-query'
import { logout } from '../api/auth'
import { SESSION_QUERY_KEY } from './useSessionQuery'

// 로그아웃은 로그인과 달리 로컬 값을 추측해 넣지 않는다(setQueryData 대신 removeQueries).
// 캐시를 비우면 세션을 구독 중인 컴포넌트가 있을 때 /auth/me를 다시 호출하게 되고,
// 로그아웃 후 서버가 실제로 준 상태(401→게스트)를 그대로 받는다.
export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: SESSION_QUERY_KEY })
    },
  })
}
