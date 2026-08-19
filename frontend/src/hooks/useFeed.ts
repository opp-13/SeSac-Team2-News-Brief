import { useQuery } from '@tanstack/react-query'
import { mockArticles } from '../mocks/feedMockData'
import type { Article } from '../types/feed'

interface UseFeedParams {
  activeFilter: string
  isLoggedIn: boolean
}

// frontend/CLAUDE.md §2 규칙2: useState+setTimeout 목업 → TanStack Query.
// TODO(§9 작업순서 이후 단계): docs/api-contracts/feed.md 확정 후 api/feed.ts + MSW 핸들러로 교체.
// 계약 없이 임의로 응답 형태를 정하지 않기 위해, 지금은 이동한 목업 배열을 그대로 필터링해
// 쿼리 함수 형태만 실제 API 호출과 동일하게 맞춰둔다.
function fetchFeed({ activeFilter, isLoggedIn }: UseFeedParams): Promise<Article[]> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const filtered =
        activeFilter === '전체'
          ? mockArticles
          : mockArticles.filter((article) =>
              isLoggedIn ? article.tags.includes(activeFilter) : article.category === activeFilter,
            )
      resolve(filtered)
    }, 700)
  })
}

export function useFeed({ activeFilter, isLoggedIn }: UseFeedParams) {
  return useQuery({
    queryKey: ['feed', activeFilter, isLoggedIn],
    queryFn: () => fetchFeed({ activeFilter, isLoggedIn }),
  })
}
