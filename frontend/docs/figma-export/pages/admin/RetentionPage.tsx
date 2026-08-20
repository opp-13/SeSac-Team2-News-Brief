import { useState } from 'react'

interface Policy {
  id: string
  name: string
  description: string
  retentionDays: number
  autoDelete: boolean
  recordCount: number
  lastRun: string
}

const POLICIES: Policy[] = [
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

export function RetentionPage() {
  const [policies, setPolicies] = useState(POLICIES)
  const [editId, setEditId] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  const update = (id: string, field: keyof Policy, value: unknown) => {
    setPolicies((prev) =>
      prev.map((p) => (p.id === id ? { ...p, [field]: value } : p))
    )
    setSaved(null)
  }

  const save = (id: string) => {
    setEditId(null)
    setSaved(id)
  }

  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
      <div className="mb-6">
        <h1 className="text-slate-900 font-semibold" style={{ fontSize: 22, letterSpacing: '-0.01em' }}>
          데이터 보관 정책
        </h1>
        <p className="text-slate-500 mt-0.5" style={{ fontSize: 13 }}>
          데이터 유형별 보관 기간 및 자동 삭제 설정
        </p>
      </div>

      <div className="space-y-3">
        {policies.map((policy) => {
          const isEditing = editId === policy.id
          return (
            <div
              key={policy.id}
              className="bg-white rounded-xl border border-slate-200 px-5 py-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h2 className="text-slate-900 font-semibold" style={{ fontSize: 15 }}>
                      {policy.name}
                    </h2>
                    {saved === policy.id && (
                      <span style={{ fontSize: 12, color: '#166534' }}>저장됨</span>
                    )}
                  </div>
                  <p className="text-slate-500" style={{ fontSize: 13 }}>{policy.description}</p>
                </div>

                <button
                  onClick={() => isEditing ? save(policy.id) : setEditId(policy.id)}
                  className="h-8 px-3 rounded-lg border border-slate-200 text-slate-700 text-[13px] hover:bg-slate-50 ml-4 shrink-0"
                  style={{ borderRadius: 8 }}
                >
                  {isEditing ? '저장' : '수정'}
                </button>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                <div>
                  <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>보관 기간</p>
                  {isEditing ? (
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        value={policy.retentionDays}
                        onChange={(e) => update(policy.id, 'retentionDays', Number(e.target.value))}
                        className="w-16 h-8 px-2 border border-slate-200 rounded text-slate-900 text-center outline-none focus:border-cyan-800"
                        style={{ fontSize: 14, borderRadius: 6 }}
                      />
                      <span className="text-slate-500" style={{ fontSize: 13 }}>일</span>
                    </div>
                  ) : (
                    <p className="text-slate-900 font-semibold" style={{ fontSize: 15, fontVariantNumeric: 'tabular-nums' }}>
                      {policy.retentionDays}일
                    </p>
                  )}
                </div>

                <div>
                  <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>자동 삭제</p>
                  {isEditing ? (
                    <button
                      onClick={() => update(policy.id, 'autoDelete', !policy.autoDelete)}
                      className="h-8 px-3 rounded-lg border border-slate-200 text-[13px]"
                      style={{
                        background: policy.autoDelete ? '#0F172A' : '#fff',
                        color: policy.autoDelete ? '#fff' : '#334155',
                        borderRadius: 6,
                      }}
                    >
                      {policy.autoDelete ? '켜짐' : '꺼짐'}
                    </button>
                  ) : (
                    <p className="font-semibold" style={{ fontSize: 15, color: policy.autoDelete ? '#166534' : '#64748B' }}>
                      {policy.autoDelete ? '켜짐' : '꺼짐'}
                    </p>
                  )}
                </div>

                <div>
                  <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>보관 중 레코드</p>
                  <p className="text-slate-900 font-semibold" style={{ fontSize: 15, fontVariantNumeric: 'tabular-nums' }}>
                    {policy.recordCount.toLocaleString()}
                  </p>
                </div>

                <div>
                  <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>마지막 실행</p>
                  <p className="text-slate-700" style={{ fontSize: 14, fontVariantNumeric: 'tabular-nums' }}>
                    {policy.lastRun}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
