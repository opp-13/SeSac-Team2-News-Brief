import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type DefaultLegendContentProps,
} from 'recharts'
import { useLLMUsage } from '../../hooks/useLLMUsage'
import { colors, typeScale, radius } from '../../constants/theme'

// docs/figma-export/pages/admin/LLMUsagePage.tsx 이식.
//
// §2 표 적용: mockDailyUsage 및 컴포넌트 내부 하드코딩 데이터(summaryCards, 모델별 분포)
// → useLLMUsage()(TanStack Query, §2 규칙2·3), named export → default export,
// 하드코딩 색상 → theme.ts 토큰(정확히 일치하는 것만 — 아래 "손대지 않은 값" 참고).
//
// design_plan.md §2 접근성 요구사항("프로바이더 색은 차트에서 점선/실선 패턴을 함께")을
// 위해 커스텀 Legend를 그린다 — Recharts 기본 Legend 아이콘이 strokeDasharray를 그대로
// 반영해준다는 보장이 없어서, 범례에서도 선 패턴이 실제로 보이는지를 직접 그려 확정한다.
//
// 손대지 않은 값 (원본 프로토타입 그대로 — 새로 판단해서 바꾸지 않음, CLAUDE.md §10):
//   - 영역 차트 채우기색 #EDE9FE/#FED7AA/#FCE7F3 — colors.provider와 같은 색상 계열의
//     연한 톤이지만 theme.ts에 톤다운 버전 토큰이 없다.
//   - "추정" 배지 fontSize 11 (요약 카드 안) — design_plan.md §3 "12px 미만 사용 금지"에
//     어긋나지만 원본 값이라 그대로 뒀다.
//   - 막대그래프 축 눈금 fontSize 11 — 위와 같은 이유로 그대로 뒀다.
//   - 배지 borderRadius 4 — theme.ts radius 스케일(6/8/12)에 없는 값이지만 그대로 뒀다.
// 토큰화·수정 여부는 확인 후 진행한다.
//
// §4 "상태 화면 4종": 로딩/오류/비어있음 구현. "끝 도달"은 이 화면에 스크롤 페이지네이션이
// 없어(집계 대시보드) 해당 없다.

const PROVIDER_STYLES = {
  openai: { stroke: colors.provider.openai, strokeDasharray: '4 2', fill: '#EDE9FE' },
  claude: { stroke: colors.provider.claude, strokeDasharray: undefined, fill: '#FED7AA' },
  gemini: { stroke: colors.provider.gemini, strokeDasharray: '2 2', fill: '#FCE7F3' },
} as const

// Recharts 기본 Legend는 dataKey를 그대로 넘겨주지 않거나 대시 패턴을 아이콘에 반영하지
// 않을 수 있어, 프로바이더별 stroke/strokeDasharray를 직접 그리는 커스텀 범례를 쓴다.
function ProviderLegend({ payload }: DefaultLegendContentProps) {
  return (
    <div
      className="flex items-center justify-center gap-4"
      style={{ paddingTop: 8, fontSize: typeScale.micro.fontSize, color: colors.muted }}
    >
      {payload?.map((entry) => {
        const dataKey = typeof entry.dataKey === 'string' ? entry.dataKey : undefined
        const style = dataKey ? PROVIDER_STYLES[dataKey as keyof typeof PROVIDER_STYLES] : undefined
        return (
          <span key={dataKey ?? String(entry.value)} className="inline-flex items-center gap-1.5">
            <svg width="16" height="8" aria-hidden="true">
              <line
                x1="0"
                y1="4"
                x2="16"
                y2="4"
                stroke={style?.stroke ?? entry.color}
                strokeWidth={2}
                strokeDasharray={style?.strokeDasharray}
              />
            </svg>
            {entry.value}
          </span>
        )
      })}
    </div>
  )
}

export default function LLMUsagePage() {
  const { data, isLoading, isError, refetch } = useLLMUsage()

  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 900 + 64, paddingLeft: 80 }}>
      <div className="mb-6">
        <h1
          className="text-slate-900 font-semibold"
          style={{ fontSize: typeScale.h1.fontSize, letterSpacing: typeScale.h1.letterSpacing }}
        >
          LLM 비용·사용량
        </h1>
        <p className="text-slate-500 mt-0.5" style={{ fontSize: typeScale.caption.fontSize }}>
          최근 7일 · 일부 값은 추정치입니다
        </p>
      </div>

      {isLoading && <UsageSkeleton />}

      {isError && <UsageErrorState onRetry={() => refetch()} />}

      {!isLoading && !isError && data && data.summary.length === 0 && <UsageEmptyState />}

      {!isLoading && !isError && data && data.summary.length > 0 && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {data.summary.map((card) => (
              <div key={card.label} className="bg-white rounded-xl border border-slate-200 px-4 py-4">
                <div className="flex items-start justify-between mb-1">
                  <p className="text-slate-500" style={{ fontSize: 12 }}>
                    {card.label}
                  </p>
                  {card.estimated && (
                    <span
                      className="inline-flex items-center px-1.5 py-0.5 rounded text-xs"
                      style={{
                        background: colors.status.partial.bg,
                        color: colors.status.partial.text,
                        fontSize: 11,
                        borderRadius: 4,
                      }}
                    >
                      추정
                    </span>
                  )}
                </div>
                <p
                  className="text-slate-900 font-semibold"
                  style={{
                    fontSize: typeScale.h1.fontSize,
                    letterSpacing: typeScale.h1.letterSpacing,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {card.value}
                  {card.unit && (
                    <span className="text-slate-400 font-normal ml-1" style={{ fontSize: 13 }}>
                      {card.unit}
                    </span>
                  )}
                </p>
              </div>
            ))}
          </div>

          {/* Cost by provider */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 mb-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-slate-900 font-semibold" style={{ fontSize: 15 }}>
                프로바이더별 비용 추이
              </h2>
              <span
                className="inline-flex items-center px-2 py-0.5 rounded text-xs"
                style={{
                  background: colors.status.partial.bg,
                  color: colors.status.partial.text,
                  fontSize: typeScale.micro.fontSize,
                  borderRadius: 4,
                }}
              >
                추정치 포함
              </span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={data.dailyUsage} margin={{ top: 4, right: 4, bottom: 0, left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12, fill: colors.muted }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: colors.muted }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `$${v}`}
                />
                <Tooltip
                  contentStyle={{ border: `1px solid ${colors.border}`, borderRadius: radius.control, fontSize: 13 }}
                  formatter={(v) => [`$${Number(v).toFixed(2)}`]}
                />
                <Legend content={ProviderLegend} />
                <Area
                  type="monotone"
                  dataKey="openai"
                  name="OpenAI"
                  stroke={PROVIDER_STYLES.openai.stroke}
                  strokeDasharray={PROVIDER_STYLES.openai.strokeDasharray}
                  fill={PROVIDER_STYLES.openai.fill}
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="claude"
                  name="Claude"
                  stroke={PROVIDER_STYLES.claude.stroke}
                  fill={PROVIDER_STYLES.claude.fill}
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="gemini"
                  name="Gemini"
                  stroke={PROVIDER_STYLES.gemini.stroke}
                  strokeDasharray={PROVIDER_STYLES.gemini.strokeDasharray}
                  fill={PROVIDER_STYLES.gemini.fill}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Model call distribution */}
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="text-slate-900 font-semibold mb-4" style={{ fontSize: 15 }}>
                모델별 호출 분포
              </h2>
              <div className="space-y-3">
                {data.modelDistribution.map((m) => (
                  <div key={m.model}>
                    <div className="flex items-center justify-between mb-1">
                      <div>
                        <span className="text-slate-800" style={{ fontSize: 13 }}>
                          {m.model}
                        </span>
                        <span className="text-slate-400 ml-2" style={{ fontSize: 12 }}>
                          {m.provider}
                        </span>
                      </div>
                      <span
                        className="text-slate-700"
                        style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums' }}
                      >
                        {m.calls.toLocaleString()}건
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${m.pct}%`,
                          background:
                            m.provider === 'Claude'
                              ? colors.provider.claude
                              : m.provider === 'OpenAI'
                                ? colors.provider.openai
                                : colors.provider.gemini,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Daily tokens */}
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-slate-900 font-semibold" style={{ fontSize: 15 }}>
                  일별 토큰 사용량
                </h2>
                <span
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs"
                  style={{
                    background: colors.status.partial.bg,
                    color: colors.status.partial.text,
                    fontSize: typeScale.micro.fontSize,
                    borderRadius: 4,
                  }}
                >
                  추정치 포함
                </span>
              </div>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={data.dailyUsage} margin={{ top: 4, right: 4, bottom: 0, left: -8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: colors.muted }} axisLine={false} tickLine={false} />
                  <YAxis
                    tick={{ fontSize: 11, fill: colors.muted }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => `${(Number(v) / 1_000_000).toFixed(1)}M`}
                  />
                  <Tooltip
                    contentStyle={{ border: `1px solid ${colors.border}`, borderRadius: radius.control, fontSize: 12 }}
                    formatter={(v) => [`${(Number(v) / 1_000_000).toFixed(2)}M 토큰`]}
                  />
                  <Bar dataKey="tokens" name="토큰" fill={colors.accent} radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function UsageSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 px-4 py-4 space-y-2">
            <div className="h-3 w-16 rounded bg-slate-100" />
            <div className="h-6 w-20 rounded bg-slate-100" />
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-4">
        <div className="h-4 w-40 rounded bg-slate-100 mb-4" />
        <div className="h-[200px] rounded bg-slate-100" />
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 h-48" />
        <div className="bg-white rounded-xl border border-slate-200 p-5 h-48" />
      </div>
    </div>
  )
}

function UsageErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-slate-200">
      <p className="text-slate-700 text-[15px] font-medium mb-1">사용량을 불러오지 못했습니다</p>
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

function UsageEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-slate-200">
      <p className="text-slate-700 text-[15px] font-medium mb-1">아직 집계된 사용량이 없습니다</p>
      <p className="text-slate-500 text-[13px]">배치가 실행되면 여기에 표시됩니다</p>
    </div>
  )
}
