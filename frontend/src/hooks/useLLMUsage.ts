import { useQuery } from '@tanstack/react-query'
import {
  mockDailyUsage,
  mockUsageSummary,
  mockModelDistribution,
} from '../mocks/llmUsageMockData'
import type { DailyUsage, UsageSummaryCard, ModelUsage } from '../types/admin'

interface LLMUsageData {
  summary: UsageSummaryCard[]
  dailyUsage: DailyUsage[]
  modelDistribution: ModelUsage[]
}

// frontend/CLAUDE.md §2 규칙2·3: 컴포넌트가 목업을 직접 들고 있는 대신 TanStack Query
// 뒤로 옮긴다 (hooks/useFeed.ts, usePipelineRuns.ts와 같은 잠정 패턴).
// TODO(§9 작업순서 이후 단계): docs/api-contracts/admin.md가 아직 없다. 계약 확정 후
// api/admin.ts + MSW 핸들러로 교체한다.
function fetchLLMUsage(): Promise<LLMUsageData> {
  return new Promise((resolve) => {
    setTimeout(
      () =>
        resolve({
          summary: mockUsageSummary,
          dailyUsage: mockDailyUsage,
          modelDistribution: mockModelDistribution,
        }),
      700,
    )
  })
}

export function useLLMUsage() {
  return useQuery({
    queryKey: ['admin', 'llm-usage'],
    queryFn: fetchLLMUsage,
  })
}
