import { useQuery } from '@tanstack/react-query'
import { fetchTags } from '../api/tags'

// 선택 가능한 전체 태그. 설정 화면, 회원가입 온보딩, 게스트 카테고리 칩이 공유한다.
// 이전에는 constants/tags.ts의 고정 상수를 썼는데, 서버가 태그 마스터를 갖고 있으므로
// (tags 테이블) 서버 값을 진실로 쓴다 — 상수와 DB가 갈라지면 저장이 조용히 실패한다.
// 태그는 거의 바뀌지 않아 staleTime을 길게 둔다.
export function useTags() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: fetchTags,
    staleTime: 10 * 60 * 1000,
  })
}
