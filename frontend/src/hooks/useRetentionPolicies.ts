import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchRetentionPolicies,
  updateRetentionPolicy,
  type RetentionPolicy,
} from '../api/admin'

const QUERY_KEY = ['admin', 'retention-policies']

export function useRetentionPolicies() {
  return useQuery({ queryKey: QUERY_KEY, queryFn: fetchRetentionPolicies })
}

/**
 * 정책 수정.
 *
 * 이전에는 "수정 → 저장"이 로컬 state만 바꿔서 새로고침하면 초기화됐다. 이제 서버에
 * 반영되고, 성공 시 목록 캐시를 그 응답으로 갱신한다 — 서버가 실제로 저장한 값과
 * 화면이 어긋나지 않게 하기 위해 입력값이 아니라 응답을 쓴다.
 */
export function useUpdateRetentionPolicy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateRetentionPolicy,
    onSuccess: (updated) => {
      queryClient.setQueryData<RetentionPolicy[]>(QUERY_KEY, (prev) =>
        prev?.map((p) => (p.id === updated.id ? updated : p)),
      )
    },
  })
}
