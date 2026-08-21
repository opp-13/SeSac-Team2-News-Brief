import { useQuery } from '@tanstack/react-query'
import { fetchPipelineRuns, fetchRunLogs, type LogLevel } from '../api/admin'

/**
 * 배치 실행 이력. `docs/api-contracts/admin.md` §1이 확정되어 목업을 걷어냈다.
 *
 * 페이지네이션은 아직 첫 페이지만 쓴다 — 화면에 "더 보기"가 없기 때문이다.
 * 서버는 커서를 내려주므로 필요해지면 useInfiniteQuery로 바꾼다.
 */
export function usePipelineRuns() {
  return useQuery({
    queryKey: ['admin', 'pipeline-runs'],
    queryFn: () => fetchPipelineRuns(),
    select: (page) => page.runs,
  })
}

/**
 * 실행 1건의 로그. 사이드 드로어가 열릴 때만 조회한다 —
 * 목록을 그릴 때 전부 미리 받아 두면 대부분 쓰이지 않는다.
 */
export function useRunLogs(runId: string | null, level?: LogLevel) {
  return useQuery({
    queryKey: ['admin', 'pipeline-logs', runId, level ?? 'ALL'],
    queryFn: () => fetchRunLogs(runId as string, level),
    enabled: runId !== null,
    select: (res) => res.logs,
  })
}
