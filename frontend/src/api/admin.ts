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
