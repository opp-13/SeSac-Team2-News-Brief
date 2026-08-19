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

export interface PipelineStage {
  name: string
  status: 'success' | 'failure' | 'running' | 'pending' | 'skipped'
  duration?: number
  count?: number
}

export interface PipelineRun {
  id: string
  executedAt: string
  relativeTime: string
  status: 'success' | 'partial' | 'failure' | 'pending'
  stages: PipelineStage[]
  processedCount: number
  errorCount: number
  provider: string
  model: string
}

export interface DailyUsage {
  date: string
  openai: number
  claude: number
  gemini: number
  tokens: number
}

export type Route =
  | '/'
  | '/login'
  | '/signup'
  | '/settings'
  | '/404'
  | '/admin/pipeline'
  | '/admin/llm-usage'
  | '/admin/retention'

export type UserTag =
  | 'AI'
  | '개발'
  | '경제'
  | '정치'
  | '스타트업'
  | '반도체'
  | '글로벌'
  | '규제'
  | '보안'
  | '모바일'
