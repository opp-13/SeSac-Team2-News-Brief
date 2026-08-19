// docs/figma-export/types.ts의 Article을 이관 (frontend/CLAUDE.md §3 "피그마 코드 이관 매핑").
// PipelineRun/DailyUsage 등 관리자용 타입은 admin.ts 이식 시 함께 옮긴다.
export interface Article {
  id: string
  source: string
  category: string
  publishedAt: string
  relativeTime: string
  headline: string
  tags: string[]
  summary: string
  url: string
  isNew?: boolean
  isRead?: boolean
}
