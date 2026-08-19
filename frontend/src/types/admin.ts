// docs/figma-export/types.ts의 관리자용 타입 이관 (frontend/CLAUDE.md §3 "피그마 코드
// 이관 매핑" — src/types.ts → types/{feed,admin}.ts 로 분할).
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

// figma-export 원본엔 없던 타입 — LLMUsagePage가 컴포넌트 내부에 하드코딩했던 요약
// 카드/모델별 분포 데이터를 목업 레이어로 옮기며 이름을 붙였다.
export interface UsageSummaryCard {
  label: string
  value: string
  unit: string
  estimated: boolean
}

export interface ModelUsage {
  model: string
  provider: string
  calls: number
  pct: number
}

// docs/figma-export/pages/admin/RetentionPage.tsx에 파일 내부 로컬로만 있던 타입 —
// 다른 admin 타입과 같은 위치로 옮겼다.
export interface RetentionPolicy {
  id: string
  name: string
  description: string
  retentionDays: number
  autoDelete: boolean
  recordCount: number
  lastRun: string
}
