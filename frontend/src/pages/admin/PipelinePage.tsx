import { useState } from 'react'
import { usePipelineRuns } from '../../hooks/usePipelineRuns'
import type { PipelineRun, PipelineStage } from '../../types/admin'
import { colors, typeScale, radius } from '../../constants/theme'
import { providerLabel } from '../../utils/provider'

// docs/figma-export/pages/admin/PipelinePage.tsx 이식.
//
// §2 표 적용: mockPipelineRuns 직접 import → usePipelineRuns()(TanStack Query, §2 규칙2),
// named export → default export, 하드코딩 색상 → theme.ts 토큰(§2 규칙5, 아래 참고).
// isLoggedIn류 prop은 원본에 없어 해당 없음 — 이 페이지는 routes/AdminRoute.tsx가
// useAuth().isAdmin으로 이미 감싸고 있다.
//
// 색상 매핑 중 theme.ts에 정확히 일치하는 토큰이 없던 것들:
//   - 단계 아이콘의 "대기"(#94A3B8→muted), "건너뜀"(#CBD5E1→border) 색 — design_plan에
//     파이프라인 단계 전용 회색 토큰이 없어 가장 가까운 기존 토큰으로 대체
//   - 오류 처리 결과 없음(#94A3B8) 표시도 동일하게 muted로 대체
//   - 경고 박스 테두리(#FDE047, yellow-300)는 대응 토큰이 없어 리터럴 유지
//   - 경고 박스 두 번째 문단 색이 원본은 #92400E(amber-800)였는데, 같은 박스 첫 문단은
//     #854D0E(status.partial.text, yellow-800)라 계열이 어긋나 있었다. 확정 토큰(yellow-800)으로
//     통일했다.
//
// §4 "상태 화면 4종": 로딩/비어있음/오류는 구현. "끝 도달"은 이 화면에 스크롤 페이지네이션이
// 없어(관리자 이력 테이블, design_plan §7에도 무한 스크롤 언급 없음) 해당 없다.

const STATUS_LABELS: Record<PipelineRun['status'], string> = {
  success: '성공',
  partial: '부분 실패',
  failure: '실패',
  pending: '대기',
}

function statusStyle(status: PipelineRun['status']) {
  switch (status) {
    case 'success':
      return colors.status.success
    case 'partial':
      return colors.status.partial
    case 'failure':
      return colors.status.error
    case 'pending':
      return colors.status.pending
  }
}

const STAGE_ICONS: Record<PipelineStage['status'], string> = {
  success: '✓',
  failure: '✗',
  running: '◐',
  pending: '○',
  skipped: '—',
}

function stageColor(status: PipelineStage['status']) {
  switch (status) {
    case 'success':
      return colors.status.success.text
    case 'failure':
      return colors.status.error.text
    case 'running':
      return colors.accent
    case 'pending':
      return colors.muted
    case 'skipped':
      return colors.border
  }
}

function stageBg(status: PipelineStage['status']) {
  switch (status) {
    case 'success':
      return colors.status.success.bg
    case 'failure':
      return colors.status.error.bg
    case 'pending':
    case 'skipped':
      return colors.status.pending.bg
    case 'running':
      return colors.accentTint
  }
}

export default function PipelinePage() {
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null)
  const { data: runs = [], isLoading, isError, refetch } = usePipelineRuns()

  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-slate-900 font-semibold"
            style={{ fontSize: typeScale.h1.fontSize, letterSpacing: typeScale.h1.letterSpacing }}
          >
            배치 실행 이력
          </h1>
          <p className="text-slate-500 mt-0.5" style={{ fontSize: typeScale.caption.fontSize }}>
            뉴스 수집·요약 파이프라인 실행 기록
          </p>
        </div>
      </div>

      {isLoading && <PipelineTableSkeleton />}

      {isError && <PipelineErrorState onRetry={() => refetch()} />}

      {!isLoading && !isError && runs.length === 0 && <PipelineEmptyState />}

      {!isLoading && !isError && runs.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full" style={{ fontVariantNumeric: 'tabular-nums' }}>
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th
                  className="text-left px-5 py-3 text-slate-500 font-medium"
                  style={{ fontSize: typeScale.micro.fontSize }}
                >
                  실행 시각
                </th>
                <th
                  className="text-left px-5 py-3 text-slate-500 font-medium"
                  style={{ fontSize: typeScale.micro.fontSize }}
                >
                  단계 진행
                </th>
                <th
                  className="text-right px-5 py-3 text-slate-500 font-medium"
                  style={{ fontSize: typeScale.micro.fontSize }}
                >
                  처리 건수
                </th>
                <th
                  className="text-right px-5 py-3 text-slate-500 font-medium"
                  style={{ fontSize: typeScale.micro.fontSize }}
                >
                  오류
                </th>
                <th
                  className="text-center px-5 py-3 text-slate-500 font-medium"
                  style={{ fontSize: typeScale.micro.fontSize }}
                >
                  상태
                </th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, idx) => {
                const st = statusStyle(run.status)
                const isLast = idx === runs.length - 1
                return (
                  <tr
                    key={run.id}
                    className="cursor-pointer transition-colors hover:bg-slate-50"
                    style={{ borderBottom: isLast ? 'none' : `1px solid ${colors.border}` }}
                    onClick={() => setSelectedRun(run)}
                    aria-selected={selectedRun?.id === run.id}
                  >
                    <td className="px-5 py-4">
                      <p className="text-slate-900" style={{ fontSize: 14 }}>
                        {run.id}
                      </p>
                      <p className="text-slate-500" style={{ fontSize: 12 }}>
                        {run.relativeTime}
                      </p>
                    </td>
                    <td className="px-5 py-4">
                      <StageBar stages={run.stages} />
                    </td>
                    <td className="px-5 py-4 text-right text-slate-900" style={{ fontSize: 14 }}>
                      {run.processedCount.toLocaleString()}
                    </td>
                    <td
                      className="px-5 py-4 text-right"
                      style={{
                        fontSize: 14,
                        color: run.errorCount > 0 ? colors.status.error.text : colors.muted,
                      }}
                    >
                      {run.errorCount > 0 ? run.errorCount.toLocaleString() : '—'}
                    </td>
                    <td className="px-5 py-4 text-center">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded-md font-medium"
                        style={{
                          background: st.bg,
                          color: st.text,
                          fontSize: typeScale.micro.fontSize,
                          borderRadius: radius.chip,
                        }}
                      >
                        {STATUS_LABELS[run.status]}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Side drawer */}
      {selectedRun && <SideDrawer run={selectedRun} onClose={() => setSelectedRun(null)} />}
    </div>
  )
}

function StageBar({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="flex items-center gap-1">
      {stages.map((stage) => (
        <div
          key={stage.name}
          title={`${stage.name}: ${stage.status}`}
          className="flex items-center justify-center w-5 h-5 rounded text-xs font-medium"
          style={{
            background: stageBg(stage.status),
            color: stageColor(stage.status),
            fontSize: 11,
          }}
        >
          {STAGE_ICONS[stage.status]}
        </div>
      ))}
    </div>
  )
}

function SideDrawer({ run, onClose }: { run: PipelineRun; onClose: () => void }) {
  const st = statusStyle(run.status)

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        // design_plan.md §6.3과 같은 계열: #0F172A(colors.primary) 30% 투명도
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
            <p className="text-slate-900 font-semibold" style={{ fontSize: 15 }}>
              실행 상세
            </p>
            <p className="text-slate-500" style={{ fontSize: 12 }}>
              {run.id}
            </p>
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
              style={{
                background: st.bg,
                color: st.text,
                fontSize: typeScale.micro.fontSize,
                borderRadius: radius.chip,
              }}
            >
              {STATUS_LABELS[run.status]}
            </span>
            <span className="text-slate-500" style={{ fontSize: 13 }}>
              {run.relativeTime}
            </span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: '처리 건수', value: run.processedCount.toLocaleString() },
              { label: '오류 건수', value: run.errorCount.toLocaleString() },
              { label: '프로바이더', value: providerLabel(run.provider) },
            ].map((s) => (
              <div key={s.label} className="bg-slate-50 rounded-lg p-3">
                <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>
                  {s.label}
                </p>
                <p
                  className="text-slate-900 font-semibold"
                  style={{ fontSize: 15, fontVariantNumeric: 'tabular-nums' }}
                >
                  {s.value}
                </p>
              </div>
            ))}
          </div>

          {/* Stages detail */}
          <div>
            <h3 className="text-slate-900 font-semibold mb-3" style={{ fontSize: 14 }}>
              단계별 상태
            </h3>
            <div className="space-y-2">
              {run.stages.map((stage) => (
                <div
                  key={stage.name}
                  className="flex items-center justify-between px-4 py-3 rounded-lg border border-slate-200"
                >
                  <div className="flex items-center gap-2">
                    <span style={{ color: stageColor(stage.status), fontSize: 14 }}>
                      {STAGE_ICONS[stage.status]}
                    </span>
                    <span className="text-slate-700" style={{ fontSize: 14 }}>
                      {stage.name}
                    </span>
                  </div>
                  <div className="text-right">
                    {stage.count !== undefined && (
                      <p
                        className="text-slate-900"
                        style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums' }}
                      >
                        {stage.count.toLocaleString()}건
                      </p>
                    )}
                    {stage.duration !== undefined && (
                      <p className="text-slate-500" style={{ fontSize: 12 }}>
                        {stage.duration}s
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Error details if any */}
          {run.errorCount > 0 && (
            <div>
              <h3 className="text-slate-900 font-semibold mb-3" style={{ fontSize: 14 }}>
                오류 내용
              </h3>
              <div
                className="rounded-lg border p-4"
                // #FDE047(yellow-300)는 대응 토큰이 없어 리터럴 유지 — colors.status.partial.bg와
                // 같은 yellow 계열의 진한 버전
                style={{ background: colors.status.partial.bg, borderColor: '#FDE047' }}
              >
                <p
                  className="font-medium mb-1"
                  style={{ fontSize: 13, color: colors.status.partial.text }}
                >
                  LLM 요약 단계에서 {run.errorCount}건 처리 실패
                </p>
                <p style={{ fontSize: 12, color: colors.status.partial.text }}>
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

function PipelineTableSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden animate-pulse">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: i < 3 ? `1px solid ${colors.border}` : 'none' }}
        >
          <div className="space-y-1.5">
            <div className="h-3.5 w-32 rounded bg-slate-100" />
            <div className="h-3 w-20 rounded bg-slate-100" />
          </div>
          <div className="flex gap-1">
            {[0, 1, 2, 3, 4].map((j) => (
              <div key={j} className="h-5 w-5 rounded bg-slate-100" />
            ))}
          </div>
          <div className="h-3.5 w-10 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  )
}

function PipelineErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-slate-200">
      <p className="text-slate-700 text-[15px] font-medium mb-1">실행 이력을 불러오지 못했습니다</p>
      <p className="text-slate-500 text-[13px] mb-4">네트워크 연결을 확인하고 다시 시도해주세요</p>
      <button
        onClick={onRetry}
        className="h-10 px-4 rounded-lg text-[14px] font-medium"
        style={{ background: colors.accent, color: colors.surface, borderRadius: radius.control }}
      >
        다시 시도
      </button>
    </div>
  )
}

function PipelineEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-slate-200">
      <p className="text-slate-700 text-[15px] font-medium mb-1">아직 실행 이력이 없습니다</p>
      <p className="text-slate-500 text-[13px]">배치가 실행되면 여기에 표시됩니다</p>
    </div>
  )
}

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}
