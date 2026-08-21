import { useState } from 'react'
import { usePipelineRuns, useRunLogs } from '../../hooks/usePipelineRuns'
import type { PipelineRun, PipelineStage, RunStatus } from '../../api/admin'
import { colors, typeScale, radius } from '../../constants/theme'
import { toRelativeTime } from '../../utils/date'

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

// 상태 값은 스키마 ENUM(대문자)을 그대로 쓴다 — 계약 §1 확정. 프로토타입은 소문자에
// `failure`(스키마는 `FAILED`)를 썼는데, 그대로 두면 같은 개념의 이름이 둘이 된다.
// run과 stage가 같은 ENUM을 쓰므로 라벨·색도 하나만 둔다.
const STATUS_LABELS: Record<RunStatus, string> = {
  SUCCESS: '성공',
  PARTIAL: '부분 실패',
  FAILED: '실패',
  PENDING: '대기',
  RUNNING: '실행 중',
}

// 단계 이름은 batch_jobs.job_type ENUM이다. 프로토타입의 5단계(뉴스 수집 / 중복 제거 /
// LLM 요약 / 태그 분류 / DB 저장) 중 뒤 셋은 ENUM에 없는 하위 작업이라, 유지하려면
// 서버가 없는 개념을 지어내야 한다 (계약 §1 "열려있는 질문" 2번 확정).
const JOB_TYPE_LABELS: Record<string, string> = {
  COLLECT: '뉴스 수집',
  SUMMARIZE: 'LLM 요약',
  TRANSLATE: '번역',
  FEED: '피드 큐레이션',
  RETENTION: '데이터 보관',
}

function statusStyle(status: RunStatus) {
  switch (status) {
    case 'SUCCESS':
      return colors.status.success
    case 'PARTIAL':
      return colors.status.partial
    case 'FAILED':
      return colors.status.error
    case 'RUNNING':
      return { bg: colors.accentTint, text: colors.accent }
    case 'PENDING':
      return colors.status.pending
  }
}

const STAGE_ICONS: Record<RunStatus, string> = {
  SUCCESS: '✓',
  FAILED: '✗',
  PARTIAL: '!',
  RUNNING: '◐',
  PENDING: '○',
}

function stageColor(status: RunStatus) {
  switch (status) {
    case 'SUCCESS':
      return colors.status.success.text
    case 'FAILED':
      return colors.status.error.text
    case 'PARTIAL':
      return colors.status.partial.text
    case 'RUNNING':
      return colors.accent
    case 'PENDING':
      return colors.muted
  }
}

function stageBg(status: RunStatus) {
  switch (status) {
    case 'SUCCESS':
      return colors.status.success.bg
    case 'FAILED':
      return colors.status.error.bg
    case 'PARTIAL':
      return colors.status.partial.bg
    case 'PENDING':
      return colors.status.pending.bg
    case 'RUNNING':
      return colors.accentTint
  }
}

/** 단계 소요 시간(초). 서버는 시각만 주고 계산은 프런트가 한다 (계약 §1). */
function stageDuration(stage: PipelineStage): number | null {
  if (!stage.startedAt || !stage.finishedAt) return null
  const ms = new Date(stage.finishedAt).getTime() - new Date(stage.startedAt).getTime()
  return ms >= 0 ? Math.round(ms / 1000) : null
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
                        {run.executedAt ? toRelativeTime(run.executedAt) : '실행 전'}
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
      {stages.map((stage, i) => (
        <div
          // job_type은 한 실행에 두 번 나올 수 있다(수집 배치를 카테고리별로 여러 번
          // 돌리면 COLLECT 행이 여러 개다). key에 순번을 함께 넣는다.
          key={`${stage.jobType}-${i}`}
          title={`${JOB_TYPE_LABELS[stage.jobType] ?? stage.jobType}: ${STATUS_LABELS[stage.status]}`}
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
              {run.executedAt ? toRelativeTime(run.executedAt) : '실행 전'}
            </span>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: '처리 건수', value: run.processedCount.toLocaleString() },
              { label: '오류 건수', value: run.errorCount.toLocaleString() },
              { label: '슬롯', value: run.slot },
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
              {run.stages.map((stage, i) => {
                const duration = stageDuration(stage)
                return (
                  <div
                    key={`${stage.jobType}-${i}`}
                    className="flex items-center justify-between px-4 py-3 rounded-lg border border-slate-200"
                  >
                    <div className="flex items-center gap-2">
                      <span style={{ color: stageColor(stage.status), fontSize: 14 }}>
                        {STAGE_ICONS[stage.status]}
                      </span>
                      <span className="text-slate-700" style={{ fontSize: 14 }}>
                        {JOB_TYPE_LABELS[stage.jobType] ?? stage.jobType}
                      </span>
                    </div>
                    <div className="text-right">
                      <p
                        className="text-slate-900"
                        style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums' }}
                      >
                        {stage.successCount.toLocaleString()}/{stage.targetCount.toLocaleString()}건
                      </p>
                      {duration !== null && (
                        <p className="text-slate-500" style={{ fontSize: 12 }}>
                          {duration}s
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 오류·경고 로그 — job_logs 실제 내용 */}
          <RunLogs runId={run.id} />
        </div>
      </div>
    </>
  )
}

/**
 * 실행 1건의 로그. 드로어가 열릴 때만 조회한다.
 *
 * 이전에는 여기에 "응답 시간 초과(timeout) 오류..." 문구가 **하드코딩**돼 있어, 어떤
 * 실행을 열어도 같은 문장이 나왔다. `job_logs`에 실제 기록이 쌓이고 있으므로 그것을 쓴다.
 *
 * INFO는 빼고 WARN/ERROR만 보여준다 — 배치가 매 실행 요약 JSON을 INFO로 남기는데,
 * 그건 "오류 내용" 자리에 놓일 성격이 아니다.
 */
function RunLogs({ runId }: { runId: string }) {
  const { data: logs = [], isLoading, isError } = useRunLogs(runId)
  const notable = logs.filter((l) => l.level === 'ERROR' || l.level === 'WARN')

  if (isLoading) {
    return <div className="h-16 rounded-lg bg-slate-100 animate-pulse" />
  }
  if (isError) {
    return (
      <p className="text-slate-500" style={{ fontSize: 13 }}>
        로그를 불러오지 못했습니다
      </p>
    )
  }
  if (notable.length === 0) {
    return (
      <div>
        <h3 className="text-slate-900 font-semibold mb-3" style={{ fontSize: 14 }}>
          오류 내용
        </h3>
        <p className="text-slate-500" style={{ fontSize: 13 }}>
          기록된 오류·경고가 없습니다
        </p>
      </div>
    )
  }

  return (
    <div>
      <h3 className="text-slate-900 font-semibold mb-3" style={{ fontSize: 14 }}>
        오류 내용 ({notable.length})
      </h3>
      <div className="space-y-2">
        {notable.map((log) => {
          const tone = log.level === 'ERROR' ? colors.status.error : colors.status.partial
          return (
            <div
              key={log.id}
              className="rounded-lg border p-4"
              style={{ background: tone.bg, borderColor: tone.bg }}
            >
              <p className="font-medium mb-1" style={{ fontSize: 13, color: tone.text }}>
                [{JOB_TYPE_LABELS[log.jobType] ?? log.jobType}] {log.errorCode ?? log.level}
                {log.retryCount > 0 && ` · 재시도 ${log.retryCount}회`}
              </p>
              {log.message && (
                <p style={{ fontSize: 12, color: tone.text, wordBreak: 'break-word' }}>
                  {log.message}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
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
