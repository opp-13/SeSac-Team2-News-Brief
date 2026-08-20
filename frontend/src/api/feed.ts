import { apiFetch } from './client'
import { toRelativeTime } from '../utils/date'
import type { Article } from '../types/feed'

// 백엔드 FeedItemResponse (backend/app/modules/feed/schemas/feed.py).
interface BackendFeedItem {
  /** 게스트 목록은 feed_items 행이 없어 null이다. 북마크에만 필요하다. */
  feedItemId: number | null
  articleId: number
  title: string
  press: string | null
  publishedAt: string
  language: string
  /** 저장된 요약이 없으면 null. 조회 시점에 생성하지 않는다(CLAUDE.md §1). */
  summary: string | null
  summaryType: string | null
  originalUrl: string
  tags: string[]
  category: string | null
}

interface BackendFeedList {
  items: BackendFeedItem[]
  nextCursor: number | null
  hasNext: boolean
}

export interface FeedPage {
  articles: Article[]
  nextCursor: number | null
  hasNext: boolean
}

export interface FetchFeedParams {
  /** 태그/카테고리 이름. '전체'는 파라미터를 보내지 않는다. */
  tag?: string
  /** 검색어 (헤더 입력창 → URL `?q=`). */
  query?: string
  cursor?: number | null
  limit?: number
}

/**
 * 백엔드 응답을 화면이 쓰는 `Article`로 바꾼다.
 *
 * 이름이 다른 필드: title→headline, press→source, originalUrl→url.
 * 계약(`docs/api-contracts/feed.md`)이 프런트 이름을 기준으로 잡혀 있지 않고
 * 백엔드가 리소스 이름을 쓰고 있어, 그 간극을 이 레이어에서 흡수한다.
 *
 * `relativeTime`은 서버가 주지 않는다 — 여기서 publishedAt으로 계산한다.
 * `isNew`는 대응하는 컬럼이 없어 채우지 않는다(스키마에 근거가 없다).
 */
function toArticle(item: BackendFeedItem): Article {
  return {
    id: String(item.articleId),
    feedItemId: item.feedItemId,
    source: item.press ?? '출처 미상',
    category: item.category ?? '',
    publishedAt: item.publishedAt,
    relativeTime: toRelativeTime(item.publishedAt),
    headline: item.title,
    tags: item.tags,
    summary: item.summary,
    url: item.originalUrl,
  }
}

export async function fetchFeed(params: FetchFeedParams = {}): Promise<FeedPage> {
  const search = new URLSearchParams()
  if (params.tag) search.set('tag', params.tag)
  if (params.query?.trim()) search.set('q', params.query.trim())
  if (params.cursor != null) search.set('cursor', String(params.cursor))
  if (params.limit != null) search.set('limit', String(params.limit))

  const qs = search.toString()
  const data = await apiFetch<BackendFeedList>(`/feed${qs ? `?${qs}` : ''}`)

  return {
    articles: data.items.map(toArticle),
    nextCursor: data.nextCursor,
    hasNext: data.hasNext,
  }
}
