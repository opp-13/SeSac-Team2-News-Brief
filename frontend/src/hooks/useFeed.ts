import { useQuery } from '@tanstack/react-query'
import { mockArticles } from '../mocks/feedMockData'
import type { Article } from '../types/feed'

interface UseFeedParams {
  activeFilter: string
  isLoggedIn: boolean
  /** 헤더 검색 입력창의 값. URL `/?q=`에서 온다. 빈 문자열이면 검색하지 않는다. */
  query?: string
}

// frontend/CLAUDE.md §2 규칙2: useState+setTimeout 목업 → TanStack Query.
// TODO(§9 작업순서 이후 단계): docs/api-contracts/feed.md 확정 후 api/feed.ts + MSW 핸들러로 교체.
// 계약 없이 임의로 응답 형태를 정하지 않기 위해, 지금은 이동한 목업 배열을 그대로 필터링해
// 쿼리 함수 형태만 실제 API 호출과 동일하게 맞춰둔다.
//
// 검색도 같은 이유로 목업 배열 위에서 처리한다. 실제로는 서버가 `GET /feed?q=`로
// 필터링해야 하는 값이다 — 클라이언트 필터는 이미 받아온 페이지 안에서만 동작하므로
// 커서 페이지네이션이 붙는 순간 "뒤쪽 페이지의 기사는 검색되지 않는" 문제가 생긴다.
function matchesQuery(article: Article, needle: string): boolean {
  if (!needle) return true
  return (
    article.headline.toLowerCase().includes(needle) ||
    article.summary.toLowerCase().includes(needle) ||
    article.source.toLowerCase().includes(needle) ||
    article.category.toLowerCase().includes(needle) ||
    article.tags.some((tag) => tag.toLowerCase().includes(needle))
  )
}

function fetchFeed({ activeFilter, isLoggedIn, query = '' }: UseFeedParams): Promise<Article[]> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const needle = query.trim().toLowerCase()
      const byFilter =
        activeFilter === '전체'
          ? mockArticles
          : mockArticles.filter((article) =>
              isLoggedIn ? article.tags.includes(activeFilter) : article.category === activeFilter,
            )
      resolve(byFilter.filter((article) => matchesQuery(article, needle)))
    }, 700)
  })
}

export function useFeed({ activeFilter, isLoggedIn, query = '' }: UseFeedParams) {
  return useQuery({
    queryKey: ['feed', activeFilter, isLoggedIn, query.trim()],
    queryFn: () => fetchFeed({ activeFilter, isLoggedIn, query }),
  })
}
