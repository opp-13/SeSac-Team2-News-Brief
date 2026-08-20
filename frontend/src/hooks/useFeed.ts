import { useQuery } from '@tanstack/react-query'
import { fetchFeed } from '../api/feed'

interface UseFeedParams {
  /** 필터 칩 선택값. '전체'는 서버에 파라미터를 보내지 않는다. */
  activeFilter: string
  /** 헤더 검색 입력창의 값(URL `?q=`). */
  query?: string
}

const ALL_FILTER = '전체'

// frontend/CLAUDE.md §2 규칙2: useState+setTimeout 목업 → TanStack Query.
// 목업 배열을 직접 감싸던 구현을 api/feed.ts 경유로 교체했다(§2 "API 호출은
// api/{module} 레이어를 경유"). 필터·검색·페이지네이션 모두 서버가 처리한다 —
// 클라이언트에서 거르면 받아온 페이지 안에서만 동작해서, 뒤쪽 페이지의 기사가
// 검색되지 않는다.
//
// 로그인 여부는 파라미터로 넘기지 않는다. 서버가 세션 쿠키로 판단해
// 게스트(articles 최신순) / 로그인(feed_items 개인화)을 나눈다.
export function useFeed({ activeFilter, query = '' }: UseFeedParams) {
  const tag = activeFilter === ALL_FILTER ? undefined : activeFilter
  const trimmed = query.trim()

  return useQuery({
    queryKey: ['feed', { tag: tag ?? null, query: trimmed }],
    queryFn: () => fetchFeed({ tag, query: trimmed }),
  })
}
