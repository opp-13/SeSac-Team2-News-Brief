import { useQuery } from '@tanstack/react-query'
import { mockPipelineRuns } from '../mocks/pipelineMockData'
import type { PipelineRun } from '../types/admin'

// frontend/CLAUDE.md §2 규칙2: 목업 데이터를 컴포넌트가 직접 import하는 대신 TanStack
// Query 뒤로 옮긴다 (hooks/useFeed.ts와 같은 잠정 패턴).
// TODO(§9 작업순서 이후 단계): docs/api-contracts/admin.md가 아직 없다. 계약 확정 후
// api/admin.ts + MSW 핸들러로 교체한다.
function fetchPipelineRuns(): Promise<PipelineRun[]> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(mockPipelineRuns), 700)
  })
}

export function usePipelineRuns() {
  return useQuery({
    queryKey: ['admin', 'pipeline-runs'],
    queryFn: fetchPipelineRuns,
  })
}
