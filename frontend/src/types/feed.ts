// docs/figma-export/types.ts의 Article을 이관 (frontend/CLAUDE.md §3 "피그마 코드 이관 매핑").
// PipelineRun/DailyUsage 등 관리자용 타입은 admin.ts 이식 시 함께 옮긴다.
//
// 백엔드 연동 후 실제 응답에 맞춰 조정한 항목:
// - `summary`가 null일 수 있다. 저장된 요약이 없는 기사다(조회 시점에 만들지 않는다 — CLAUDE.md §1).
// - `feedItemId`를 추가했다. 북마크 API가 feed_items 행 id를 받고, 게스트는 이 값이 없다.
// - `relativeTime`은 서버 값이 아니라 utils/date.ts가 publishedAt으로 계산한 표시용 문자열이다.
export interface Article {
  /** articles.id 문자열. BIGINT라 number로 다루지 않는다. */
  id: string
  /** 게스트 목록에서는 null (feed_items 행이 없다). 북마크에 필요하다. */
  feedItemId?: number | null
  source: string
  /** 카테고리 매핑이 없으면 빈 문자열. */
  category: string
  publishedAt: string
  /** 표시용 파생값 — 서버가 주지 않는다. */
  relativeTime: string
  headline: string
  tags: string[]
  /** 저장된 요약이 없으면 null. */
  summary: string | null
  url: string
  /**
   * "속보" 앰버 점 표시용.
   *
   * **API가 채우지 않는다.** 대응하는 컬럼이 스키마에 없다
   * (`docs/api-contracts/feed.md`에 "스키마에 없음 — 정의 필요"로 기록해 둔 항목).
   * 디자인 요소라 타입과 UI는 남겨 두되, 근거가 정해질 때까지 값은 오지 않는다.
   * `publishedAt`이 최근이라는 이유로 프런트가 임의로 만들지 않는다 — "속보"의 의미를
   * 프런트가 정하는 셈이 된다.
   */
  isNew?: boolean
  /** 클라이언트에서만 추적하는 읽음 표시 (서버 컬럼 미연동). */
  isRead?: boolean
}
