import { apiFetch } from './client'

/** 백엔드 `GET /admin/retention` 응답 1건 (retention_policies + 파생 recordCount). */
interface BackendRetentionPolicy {
  targetEntity: string
  retentionDays: number
  strategy: string
  isActive: boolean
  recordCount: number
  lastExecutedAt: string | null
}

/**
 * 화면이 쓰는 형태.
 *
 * `name` / `description`은 서버가 보내지 않는다 — 표시용 문구라 프런트가 갖는다
 * (`docs/api-contracts/admin.md` "이름·설명 문구는 어디서 오는가" (a)안).
 * 서버가 표시 문구를 만들면 문구를 고칠 때마다 백엔드를 배포해야 한다.
 */
export interface RetentionPolicy {
  /** targetEntity가 유일 키라 그대로 식별자로 쓴다. */
  id: string
  name: string
  description: string
  retentionDays: number
  autoDelete: boolean
  recordCount: number
  /** 마지막 실행 시각. 한 번도 안 돌았으면 null — 화면은 `—`로 표시한다. */
  lastRun: string | null
}

const LABELS: Record<string, { name: string; description: string }> = {
  ARTICLES: {
    name: '기사 원문',
    description: '수집된 원문 본문. 삭제 시 요약·번역·피드가 함께 사라진다',
  },
  SUMMARIES: { name: 'AI 요약', description: 'LLM이 생성한 요약문' },
  TRANSLATIONS: { name: '번역문', description: '요약문의 다국어 번역 결과' },
  FEED_ITEMS: { name: '개인화 피드', description: '큐레이션 배치가 만든 사용자별 피드 행' },
  LOGS: { name: '배치 로그', description: '수집·처리 오류 및 재시도 이력' },
}

function toPolicy(p: BackendRetentionPolicy): RetentionPolicy {
  const label = LABELS[p.targetEntity] ?? { name: p.targetEntity, description: '' }
  return {
    id: p.targetEntity,
    name: label.name,
    description: label.description,
    retentionDays: p.retentionDays,
    autoDelete: p.isActive,
    recordCount: p.recordCount,
    lastRun: p.lastExecutedAt,
  }
}

export function fetchRetentionPolicies(): Promise<RetentionPolicy[]> {
  return apiFetch<BackendRetentionPolicy[]>('/admin/retention').then((rows) => rows.map(toPolicy))
}

export interface RetentionPolicyUpdate {
  targetEntity: string
  retentionDays?: number
  isActive?: boolean
}

/** 부분 수정. 화면이 편집할 수 있는 값은 보관 일수와 자동 삭제 여부뿐이다. */
export function updateRetentionPolicy(input: RetentionPolicyUpdate): Promise<RetentionPolicy> {
  const { targetEntity, ...body } = input
  return apiFetch<BackendRetentionPolicy>(`/admin/retention/${targetEntity}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  }).then(toPolicy)
}

// ─────────────────────────────────────────────────────────
// 배치 실행 이력 (docs/api-contracts/admin.md §1)
//
// 이 타입들은 `types/admin.ts`에 있었는데 그 파일은 피그마 프로토타입 기준이라
// 실제 응답과 어긋나 있었다(소문자 status, 서버가 만들지 않는 `relativeTime`,
// 삭제된 `ai_invocations`에서 오던 `provider`/`model`). 계약 확정본에 맞춰 이리로
// 옮기면서 정리했고, 남은 export가 없어 그 파일은 삭제했다.
// ─────────────────────────────────────────────────────────

/**
 * 상태 값은 스키마 ENUM(대문자)을 그대로 쓴다. 프로토타입이 쓰던 소문자
 * (`'success' | 'failure'`)로 바꾸면 진실 공급원이 둘이 된다 — 계약 §1 확정 사항.
 */
export type RunStatus = 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'PENDING' | 'RUNNING'

export interface PipelineStage {
  jobType: string
  status: RunStatus
  targetCount: number
  successCount: number
  failCount: number
  startedAt: string | null
  finishedAt: string | null
}

export interface PipelineRun {
  /** `20260821-0700` — 날짜+slot 합성. 서버가 저장하지 않고 매번 계산한다. */
  id: string
  slot: string
  status: RunStatus
  executedAt: string | null
  /**
   * 단계 success_count의 **합**이라 같은 기사가 여러 단계를 지나면 중복 집계된다.
   * 배치마다 success_count의 단위가 다른 것도 아직 정리되지 않았다
   * (계약 §1 "열려있는 질문" 5번 — A·B·C 합의 대기).
   */
  processedCount: number
  errorCount: number
  stages: PipelineStage[]
}

export interface PipelineRunPage {
  runs: PipelineRun[]
  nextCursor: string | null
  hasNext: boolean
}

export function fetchPipelineRuns(cursor?: string | null, limit = 20): Promise<PipelineRunPage> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) params.set('cursor', cursor)
  return apiFetch<PipelineRunPage>(`/admin/pipeline/runs?${params}`)
}

export type LogLevel = 'INFO' | 'WARN' | 'ERROR'

export interface JobLog {
  /** BIGINT라 서버가 문자열로 보낸다 (JS 안전 정수 범위). */
  id: string
  jobType: string
  articleId: string | null
  level: LogLevel
  errorCode: string | null
  message: string | null
  retryCount: number
  createdAt: string
}

/** `level`을 생략하면 전체 등급을 받는다. */
export function fetchRunLogs(runId: string, level?: LogLevel): Promise<{ logs: JobLog[] }> {
  const qs = level ? `?level=${level}` : ''
  return apiFetch<{ logs: JobLog[] }>(`/admin/pipeline/runs/${runId}/logs${qs}`)
}
