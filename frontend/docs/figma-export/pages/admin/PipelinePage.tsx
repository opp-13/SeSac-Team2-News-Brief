import { useState } from 'react'
import { mockPipelineRuns } from '../../data/mockData'
import type { PipelineRun, PipelineStage } from '../../types'

const STATUS_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  success: { bg: '#DCFCE7', color: '#166534', label: '성공' },
  partial: { bg: '#FEF9C3', color: '#854D0E', label: '부분 실패' },
  failure: { bg: '#FEE2E2', color: '#991B1B', label: '실패' },
  pending: { bg: '#F1F5F9', color: '#334155', label: '대기' },
}

const STAGE_STATUS_STYLES: Record<string, { color: string; icon: string }> = {
  success: { color: '#166534', icon: '✓' },
  failure: { color: '#991B1B', icon: '✗' },
  running: { color: '#155E75', icon: '◐' },
  pending: { color: '#94A3B8', icon: '○' },
  skipped: { color: '#CBD5E1', icon: '—' },
}

export function PipelinePage() {
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null)

  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-slate-900 font-semibold" style={{ fontSize: 22, letterSpacing: '-0.01em' }}>
            배치 실행 이력
          </h1>
          <p className="text-slate-500 mt-0.5" style={{ fontSize: 13 }}>
            뉴스 수집·요약 파이프라인 실행 기록
          </p>
        </div>
      </div>

      {/* Pipeline list */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full" style={{ fontVariantNumeric: 'tabular-nums' }}>
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="text-left px-5 py-3 text-slate-500 font-medium" style={{ fontSize: 12 }}>실행 시각</th>
              <th className="text-left px-5 py-3 text-slate-500 font-medium" style={{ fontSize: 12 }}>단계 진행</th>
              <th className="text-right px-5 py-3 text-slate-500 font-medium" style={{ fontSize: 12 }}>처리 건수</th>
              <th className="text-right px-5 py-3 text-slate-500 font-medium" style={{ fontSize: 12 }}>오류</th>
              <th className="text-center px-5 py-3 text-slate-500 font-medium" style={{ fontSize: 12 }}>상태</th>
            </tr>
          </thead>
          <tbody>
            {mockPipelineRuns.map((run, idx) => {
              const st = STATUS_STYLES[run.status]
              const isLast = idx === mockPipelineRuns.length - 1
              return (
                <tr
                  key={run.id}
                  className="cursor-pointer transition-colors hover:bg-slate-50"
                  style={{ borderBottom: isLast ? 'none' : '1px solid #E2E8F0' }}
                  onClick={() => setSelectedRun(run)}
                  aria-selected={selectedRun?.id === run.id}
                >
                  <td className="px-5 py-4">
                    <p className="text-slate-900" style={{ fontSize: 14 }}>{run.id}</p>
                    <p className="text-slate-500" style={{ fontSize: 12 }}>{run.relativeTime}</p>
                  </td>
                  <td className="px-5 py-4">
                    <StageBar stages={run.stages} />
                  </td>
                  <td className="px-5 py-4 text-right text-slate-900" style={{ fontSize: 14 }}>
                    {run.processedCount.toLocaleString()}
                  </td>
                  <td className="px-5 py-4 text-right" style={{ fontSize: 14, color: run.errorCount > 0 ? '#991B1B' : '#94A3B8' }}>
                    {run.errorCount > 0 ? run.errorCount.toLocaleString() : '—'}
                  </td>
                  <td className="px-5 py-4 text-center">
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-md font-medium"
                      style={{ background: st.bg, color: st.color, fontSize: 12, borderRadius: 6 }}
                    >
                      {st.label}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Side drawer */}
      {selectedRun && (
        <SideDrawer run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
    </div>
  )
}

function StageBar({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="flex items-center gap-1">
      {stages.map((stage) => {
        const s = STAGE_STATUS_STYLES[stage.status]
        return (
          <div
            key={stage.name}
            title={`${stage.name}: ${stage.status}`}
            className="flex items-center justify-center w-5 h-5 rounded text-xs font-medium"
            style={{
              background: stage.status === 'success' ? '#DCFCE7' : stage.status === 'failure' ? '#FEE2E2' : stage.status === 'pending' || stage.status === 'skipped' ? '#F1F5F9' : '#CFFAFE',
              color: s.color,
              fontSize: 11,
            }}
          >
            {s.icon}
          </div>
        )
      })}
    </div>
  )
}

function SideDrawer({ run, onClose }: { run: PipelineRun; onClose: () => void }) {
  const st = STATUS_STYLES[run.status]

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ background: 'rgba(15,23,42,0.3)' }}
        onClick={onClose}
      />
      <div
        className="fixed right-0 top-0 h-full bg-white border-l border-slate-200 z-50 overflow-y-auto"
        style={{ width: 480 }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-slate-900 font-semibold" style={{ fontSize: 15 }}>실행 상세</p>
            <p className="text-slate-500" style={{ fontSize: 12 }}>{run.id}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Summary */}
          <div className="flex items-center gap-3">
            <span
              className="inline-flex items-center px-2 py-1 rounded-md font-medium"
              style={{ background: st.bg, color: st.color, fontSize: 12, borderRadius: 6 }}
            >
              {st.label}
            </span>
            <span className="text-slate-500" style={{ fontSize: 13 }}>{run.relativeTime}</span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: '처리 건수', value: run.processedCount.toLocaleString() },
              { label: '오류 건수', value: run.errorCount.toLocaleString() },
              { label: '프로바이더', value: run.provider },
            ].map((s) => (
              <div key={s.label} className="bg-slate-50 rounded-lg p-3">
                <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>{s.label}</p>
                <p className="text-slate-900 font-semibold" style={{ fontSize: 15, fontVariantNumeric: 'tabular-nums' }}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Stages detail */}
          <div>
            <h3 className="text-slate-900 font-semibold mb-3" style={{ fontSize: 14 }}>단계별 상태</h3>
            <div className="space-y-2">
              {run.stages.map((stage) => {
                const s = STAGE_STATUS_STYLES[stage.status]
                return (
                  <div
                    key={stage.name}
                    className="flex items-center justify-between px-4 py-3 rounded-lg border border-slate-200"
                  >
                    <div className="flex items-center gap-2">
                      <span style={{ color: s.color, fontSize: 14 }}>{s.icon}</span>
                      <span className="text-slate-700" style={{ fontSize: 14 }}>{stage.name}</span>
                    </div>
                    <div className="text-right">
                      {stage.count !== undefined && (
                        <p className="text-slate-900" style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums' }}>
                          {stage.count.toLocaleString()}건
                        </p>
                      )}
                      {stage.duration !== undefined && (
                        <p className="text-slate-500" style={{ fontSize: 12 }}>{stage.duration}s</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Error details if any */}
          {run.errorCount > 0 && (
            <div>
              <h3 className="text-slate-900 font-semibold mb-3" style={{ fontSize: 14 }}>오류 내용</h3>
              <div
                className="rounded-lg border p-4"
                style={{ background: '#FEF9C3', borderColor: '#FDE047' }}
              >
                <p className="font-medium mb-1" style={{ fontSize: 13, color: '#854D0E' }}>
                  LLM 요약 단계에서 {run.errorCount}건 처리 실패
                </p>
                <p style={{ fontSize: 12, color: '#92400E' }}>
                  응답 시간 초과(timeout) 오류. Rate limit 초과로 인한 재시도 실패.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}
