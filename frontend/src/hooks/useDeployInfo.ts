import { useQuery } from '@tanstack/react-query'
import { fetchDeployInfo } from '../api/meta'

// 배포 검증용 정보(서버 IP/명, 클라이언트 IP/XFF, API 버전)는 자주 바뀌지 않으니
// staleTime을 길게 두고, 실패해도 화면 전체를 막지 않도록 재시도는 최소로 둔다.
export function useDeployInfo() {
  return useQuery({
    queryKey: ['meta', 'deploy-info'],
    queryFn: fetchDeployInfo,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}
