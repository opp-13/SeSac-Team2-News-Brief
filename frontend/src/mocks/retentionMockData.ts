import type { RetentionPolicy } from '../types/admin'

// docs/figma-export/pages/admin/RetentionPage.tsx의 POLICIES 상수를 이관
// (frontend/CLAUDE.md §2 규칙2·3 — 컴포넌트가 데이터를 직접 들고 있지 않게).
export const mockRetentionPolicies: RetentionPolicy[] = [
  {
    id: 'articles',
    name: '기사 원문',
    description: '수집된 원문 HTML 및 텍스트 데이터',
    retentionDays: 90,
    autoDelete: true,
    recordCount: 128_402,
    lastRun: '2026-08-18',
  },
  {
    id: 'summaries',
    name: 'AI 요약문',
    description: 'LLM이 생성한 요약 텍스트',
    retentionDays: 180,
    autoDelete: true,
    recordCount: 87_291,
    lastRun: '2026-08-18',
  },
  {
    id: 'logs',
    name: '파이프라인 로그',
    description: '배치 실행 로그 및 오류 기록',
    retentionDays: 30,
    autoDelete: true,
    recordCount: 4_820,
    lastRun: '2026-08-19',
  },
  {
    id: 'llm_calls',
    name: 'LLM 호출 이력',
    description: 'API 요청·응답 메타데이터 (본문 제외)',
    retentionDays: 365,
    autoDelete: false,
    recordCount: 18_294,
    lastRun: '—',
  },
]
