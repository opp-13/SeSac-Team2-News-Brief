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
} from 'recharts'
import { mockDailyUsage } from '../../data/mockData'

const PROVIDER_COLORS = {
  openai: { stroke: '#6D28D9', strokeDasharray: '4 2' },
  claude: { stroke: '#C2410C', strokeDasharray: undefined },
  gemini: { stroke: '#BE185D', strokeDasharray: '2 2' },
}

const summaryCards = [
  { label: '총 호출 수', value: '18,294', unit: '건', estimated: false },
  { label: '총 토큰', value: '33.0M', unit: '토큰', estimated: true },
  { label: '예상 비용', value: '$26.80', unit: '', estimated: true },
  { label: '실패율', value: '2.3%', unit: '', estimated: false },
]

export function LLMUsagePage() {
  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 900 + 64, paddingLeft: 80 }}>
      <div className="mb-6">
        <h1 className="text-slate-900 font-semibold" style={{ fontSize: 22, letterSpacing: '-0.01em' }}>
          LLM 비용·사용량
        </h1>
        <p className="text-slate-500 mt-0.5" style={{ fontSize: 13 }}>
          최근 7일 · 일부 값은 추정치입니다
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {summaryCards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl border border-slate-200 px-4 py-4">
            <div className="flex items-start justify-between mb-1">
              <p className="text-slate-500" style={{ fontSize: 12 }}>{card.label}</p>
              {card.estimated && (
                <span
                  className="inline-flex items-center px-1.5 py-0.5 rounded text-xs"
                  style={{ background: '#FEF9C3', color: '#854D0E', fontSize: 11, borderRadius: 4 }}
                >
                  추정
                </span>
              )}
            </div>
            <p
              className="text-slate-900 font-semibold"
              style={{ fontSize: 22, letterSpacing: '-0.01em', fontVariantNumeric: 'tabular-nums' }}
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
            style={{ background: '#FEF9C3', color: '#854D0E', fontSize: 12, borderRadius: 4 }}
          >
            추정치 포함
          </span>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={mockDailyUsage} margin={{ top: 4, right: 4, bottom: 0, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#64748B' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              contentStyle={{ border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 13 }}
              formatter={(v) => [`$${Number(v).toFixed(2)}`]}
            />
            <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
            <Area
              type="monotone"
              dataKey="openai"
              name="OpenAI"
              stroke={PROVIDER_COLORS.openai.stroke}
              strokeDasharray={PROVIDER_COLORS.openai.strokeDasharray}
              fill="#EDE9FE"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="claude"
              name="Claude"
              stroke={PROVIDER_COLORS.claude.stroke}
              fill="#FED7AA"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="gemini"
              name="Gemini"
              stroke={PROVIDER_COLORS.gemini.stroke}
              strokeDasharray={PROVIDER_COLORS.gemini.strokeDasharray}
              fill="#FCE7F3"
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
            {[
              { model: 'claude-sonnet-5', provider: 'Claude', calls: 9840, pct: 54 },
              { model: 'gpt-4o', provider: 'OpenAI', calls: 6230, pct: 34 },
              { model: 'gemini-2.0-flash', provider: 'Gemini', calls: 2224, pct: 12 },
            ].map((m) => (
              <div key={m.model}>
                <div className="flex items-center justify-between mb-1">
                  <div>
                    <span className="text-slate-800" style={{ fontSize: 13 }}>{m.model}</span>
                    <span className="text-slate-400 ml-2" style={{ fontSize: 12 }}>{m.provider}</span>
                  </div>
                  <span className="text-slate-700" style={{ fontSize: 13, fontVariantNumeric: 'tabular-nums' }}>
                    {m.calls.toLocaleString()}건
                  </span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${m.pct}%`,
                      background: m.provider === 'Claude' ? '#C2410C' : m.provider === 'OpenAI' ? '#6D28D9' : '#BE185D',
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
              style={{ background: '#FEF9C3', color: '#854D0E', fontSize: 12, borderRadius: 4 }}
            >
              추정치 포함
            </span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={mockDailyUsage} margin={{ top: 4, right: 4, bottom: 0, left: -8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(Number(v) / 1_000_000).toFixed(1)}M`} />
              <Tooltip
                contentStyle={{ border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 12 }}
                formatter={(v) => [`${(Number(v) / 1_000_000).toFixed(2)}M 토큰`]}
              />
              <Bar dataKey="tokens" name="토큰" fill="#155E75" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
