import type { DailyUsage, UsageSummaryCard, ModelUsage } from '../types/admin'

// docs/figma-export/data/mockData.ts의 mockDailyUsage를 이관. summaryCards/모델별 분포는
// 원본 LLMUsagePage.tsx 컴포넌트 안에 하드코딩돼 있던 걸 같은 이유(§2 규칙2·3)로
// 여기로 옮겼다 — 컴포넌트가 더 이상 상수 데이터를 직접 들고 있지 않게.
export const mockDailyUsage: DailyUsage[] = [
  { date: '08/13', openai: 1.24, claude: 2.18, gemini: 0.43, tokens: 4_820_000 },
  { date: '08/14', openai: 1.31, claude: 2.05, gemini: 0.38, tokens: 5_140_000 },
  { date: '08/15', openai: 0.98, claude: 1.87, gemini: 0.51, tokens: 4_390_000 },
  { date: '08/16', openai: 1.45, claude: 2.34, gemini: 0.29, tokens: 5_680_000 },
  { date: '08/17', openai: 1.22, claude: 2.11, gemini: 0.44, tokens: 4_910_000 },
  { date: '08/18', openai: 1.38, claude: 2.29, gemini: 0.36, tokens: 5_320_000 },
  { date: '08/19', openai: 0.72, claude: 1.14, gemini: 0.18, tokens: 2_740_000 },
]

export const mockUsageSummary: UsageSummaryCard[] = [
  { label: '총 호출 수', value: '18,294', unit: '건', estimated: false },
  { label: '총 토큰', value: '33.0M', unit: '토큰', estimated: true },
  { label: '예상 비용', value: '$26.80', unit: '', estimated: true },
  { label: '실패율', value: '2.3%', unit: '', estimated: false },
]

export const mockModelDistribution: ModelUsage[] = [
  { model: 'claude-sonnet-5', provider: 'Claude', calls: 9840, pct: 54 },
  { model: 'gpt-4o', provider: 'OpenAI', calls: 6230, pct: 34 },
  { model: 'gemini-2.0-flash', provider: 'Gemini', calls: 2224, pct: 12 },
]
