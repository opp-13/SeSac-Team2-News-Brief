// docs/figma-export/types.ts의 관리자용 타입 이관 (frontend/CLAUDE.md §3 "피그마 코드
// 이관 매핑" — src/types.ts → types/{feed,admin}.ts 로 분할).
//
// provider 값은 스키마 V2의 `provider` 컬럼을 따른다('openai'/'anthropic'/'google').
// 프로토타입이 쓰던 표시용 문자열('OpenAI'/'Claude'/'Gemini')은 데이터가 아니라 라벨이므로
// utils/provider.ts 의 providerLabel()로 화면에서 붙인다.
import type { Provider } from '../utils/provider'

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
  provider: Provider
  model: string
}

// 프로바이더별 일일 비용. 키가 곧 차트 series의 dataKey이고 theme.ts colors.provider의 키다.
//
// [TODO-계약] 실제 응답은 고정 키가 아니라 `costByProvider[]` 배열이다
// (docs/api-contracts/admin.md). 프로바이더가 늘어도 계약이 깨지지 않게 하려는 형태인데,
// 차트를 배열 소비로 바꾸는 것은 A·B의 집계 API가 붙는 시점에 함께 한다.
// 지금은 목업이 고정 3종이라 키 이름만 스키마 값에 맞춰 뒀다.
export interface DailyUsage {
  date: string
  openai: number
  anthropic: number
  google: number
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
  provider: Provider
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
