import { useMutation, useQueryClient } from '@tanstack/react-query'
import { saveUserTags } from '../api/auth'
import { SESSION_QUERY_KEY } from './useSessionQuery'
import type { Session } from '../api/auth'

// frontend/CLAUDE.md §2 규칙4: onSaveTags prop → 훅. 세션(userTags 포함)은
// useSessionQuery(['auth','me']) 캐시가 유일한 진실 공급원이라, 저장 성공 시 그
// 캐시의 userTags 필드만 갱신한다(로그인/로그아웃과 같은 패턴).
export function useSaveUserTags() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: saveUserTags,
    onSuccess: (userTags) => {
      queryClient.setQueryData<Session>(SESSION_QUERY_KEY, (prev) =>
        prev ? { ...prev, userTags } : prev,
      )
    },
  })
}
