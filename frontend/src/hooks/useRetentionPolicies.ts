import { useQuery } from '@tanstack/react-query'
import { mockRetentionPolicies } from '../mocks/retentionMockData'
import type { RetentionPolicy } from '../types/admin'

// frontend/CLAUDE.md §2 규칙2·3: 컴포넌트가 목업 상수를 직접 들고 있는 대신 TanStack
// Query 뒤로 옮긴다 (hooks/useFeed.ts, usePipelineRuns.ts, useLLMUsage.ts와 같은 패턴).
// TODO(§9 작업순서 이후 단계): docs/api-contracts/admin.md가 아직 없다. 계약 확정 후
// api/admin.ts + MSW 핸들러(조회)와 정책 수정을 위한 별도 mutation 엔드포인트로 교체한다.
// "수정 저장"은 실제로 서버에 반영되지 않는 로컬 전용 동작이라 이 훅은 조회만 담당한다
// (원본 프로토타입도 새로고침하면 편집 내용이 사라지는 동작이었다 — 그대로 유지).
function fetchRetentionPolicies(): Promise<RetentionPolicy[]> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(mockRetentionPolicies), 700)
  })
}

export function useRetentionPolicies() {
  return useQuery({
    queryKey: ['admin', 'retention-policies'],
    queryFn: fetchRetentionPolicies,
  })
}
