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

// RetentionPolicy는 api/admin.ts가 소유한다 — 서버 응답을 화면 형태로 바꾸는
// 매핑과 같은 자리에 두는 편이 어긋날 여지가 적다.
