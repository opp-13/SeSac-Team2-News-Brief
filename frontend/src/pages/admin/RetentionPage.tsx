import { useState } from 'react'
import { useRetentionPolicies } from '../../hooks/useRetentionPolicies'
import type { RetentionPolicy } from '../../types/admin'
import { colors, typeScale, radius } from '../../constants/theme'

// docs/figma-export/pages/admin/RetentionPage.tsx 이식.
//
// §2 표 적용: 컴포넌트 파일에 하드코딩돼 있던 POLICIES 상수 → useRetentionPolicies()
// (TanStack Query, §2 규칙2·3), named export → default export, 하드코딩 색상 →
// theme.ts 토큰(정확히 일치하는 것만 — 나머지는 원본 값 그대로 손대지 않음, CLAUDE.md §10).
//
// "수정/저장"은 원본도 서버에 반영하지 않는 로컬 전용 동작이라(새로고침하면 초기화)
// 그 구조를 그대로 유지한다 — 조회 결과(policies)를 로컬 편집용 state로 한 번만 복사해
// 두고, 이후 편집은 이 로컬 state에서만 일어난다. 편집 중에 백그라운드 재검증이 와도
// 사용자가 고치던 값을 덮어쓰지 않도록 "최초 한 번만 시드"하는 패턴을 쓴다(useEffect
// 대신 렌더 중 상태 조정 — NewsFeedPage의 prevActiveFilter와 같은 이유).
//
// §4 "상태 화면 4종": 로딩/오류/비어있음 구현. "끝 도달"은 스크롤 페이지네이션이 없어
// (정책 목록은 고정된 소수 항목) 해당 없다.

export default function RetentionPage() {
  const { data, isLoading, isError, refetch } = useRetentionPolicies()
  const [policies, setPolicies] = useState<RetentionPolicy[]>([])
  const [hasSeeded, setHasSeeded] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  // 최초 조회가 끝난 시점에 딱 한 번만 로컬 편집용 state로 복사한다. 이후 백그라운드
  // 재검증이 다시 성공해도(예: 실제 API로 교체된 뒤) 사용자가 편집 중인 값을
  // 덮어쓰지 않는다.
  if (data && !hasSeeded) {
    setHasSeeded(true)
    setPolicies(data)
  }

  const update = (id: string, field: keyof RetentionPolicy, value: unknown) => {
    setPolicies((prev) => prev.map((p) => (p.id === id ? { ...p, [field]: value } : p)))
    setSaved(null)
  }

  const save = (id: string) => {
    setEditId(null)
    setSaved(id)
  }

  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
      <div className="mb-6">
        <h1
          className="text-slate-900 font-semibold"
          style={{ fontSize: typeScale.h1.fontSize, letterSpacing: typeScale.h1.letterSpacing }}
        >
          데이터 보관 정책
        </h1>
        <p className="text-slate-500 mt-0.5" style={{ fontSize: typeScale.caption.fontSize }}>
          데이터 유형별 보관 기간 및 자동 삭제 설정
        </p>
      </div>

      {isLoading && <RetentionSkeleton />}

      {isError && <RetentionErrorState onRetry={() => refetch()} />}

      {!isLoading && !isError && data && policies.length === 0 && <RetentionEmptyState />}

      {!isLoading && !isError && data && policies.length > 0 && (
        <div className="space-y-3">
          {policies.map((policy) => {
            const isEditing = editId === policy.id
            return (
              <div key={policy.id} className="bg-white rounded-xl border border-slate-200 px-5 py-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h2 className="text-slate-900 font-semibold" style={{ fontSize: 15 }}>
                        {policy.name}
                      </h2>
                      {saved === policy.id && (
                        <span style={{ fontSize: 12, color: colors.status.success.text }}>저장됨</span>
                      )}
                    </div>
                    <p className="text-slate-500" style={{ fontSize: typeScale.caption.fontSize }}>
                      {policy.description}
                    </p>
                  </div>

                  <button
                    onClick={() => (isEditing ? save(policy.id) : setEditId(policy.id))}
                    className="h-8 px-3 rounded-lg border border-slate-200 text-slate-700 text-[13px] hover:bg-slate-50 ml-4 shrink-0"
                    style={{ borderRadius: radius.control }}
                  >
                    {isEditing ? '저장' : '수정'}
                  </button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                  <div>
                    <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>
                      보관 기간
                    </p>
                    {isEditing ? (
                      <div className="flex items-center gap-1">
                        <input
                          type="number"
                          value={policy.retentionDays}
                          onChange={(e) => update(policy.id, 'retentionDays', Number(e.target.value))}
                          className="w-16 h-8 px-2 border border-slate-200 rounded text-slate-900 text-center outline-none focus:border-cyan-800"
                          style={{ fontSize: 14, borderRadius: radius.chip }}
                        />
                        <span className="text-slate-500" style={{ fontSize: typeScale.caption.fontSize }}>
                          일
                        </span>
                      </div>
                    ) : (
                      <p
                        className="text-slate-900 font-semibold"
                        style={{ fontSize: 15, fontVariantNumeric: 'tabular-nums' }}
                      >
                        {policy.retentionDays}일
                      </p>
                    )}
                  </div>

                  <div>
                    <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>
                      자동 삭제
                    </p>
                    {isEditing ? (
                      <button
                        onClick={() => update(policy.id, 'autoDelete', !policy.autoDelete)}
                        className="h-8 px-3 rounded-lg border border-slate-200 text-[13px]"
                        style={{
                          background: policy.autoDelete ? colors.primary : colors.surface,
                          color: policy.autoDelete ? colors.surface : colors.neutral.text,
                          borderRadius: radius.chip,
                        }}
                      >
                        {policy.autoDelete ? '켜짐' : '꺼짐'}
                      </button>
                    ) : (
                      <p
                        className="font-semibold"
                        style={{
                          fontSize: 15,
                          color: policy.autoDelete ? colors.status.success.text : colors.muted,
                        }}
                      >
                        {policy.autoDelete ? '켜짐' : '꺼짐'}
                      </p>
                    )}
                  </div>

                  <div>
                    <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>
                      보관 중 레코드
                    </p>
                    <p
                      className="text-slate-900 font-semibold"
                      style={{ fontSize: 15, fontVariantNumeric: 'tabular-nums' }}
                    >
                      {policy.recordCount.toLocaleString()}
                    </p>
                  </div>

                  <div>
                    <p className="text-slate-500 mb-1" style={{ fontSize: 12 }}>
                      마지막 실행
                    </p>
                    <p className="text-slate-700" style={{ fontSize: 14, fontVariantNumeric: 'tabular-nums' }}>
                      {policy.lastRun}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function RetentionSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 px-5 py-4">
          <div className="h-4 w-24 rounded bg-slate-100 mb-2" />
          <div className="h-3 w-48 rounded bg-slate-100 mb-4" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[0, 1, 2, 3].map((j) => (
              <div key={j} className="space-y-1.5">
                <div className="h-3 w-16 rounded bg-slate-100" />
                <div className="h-4 w-12 rounded bg-slate-100" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function RetentionErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-slate-200">
      <p className="text-slate-700 text-[15px] font-medium mb-1">보관 정책을 불러오지 못했습니다</p>
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

function RetentionEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center bg-white rounded-xl border border-slate-200">
      <p className="text-slate-700 text-[15px] font-medium mb-1">설정된 보관 정책이 없습니다</p>
      <p className="text-slate-500 text-[13px]">데이터 유형이 추가되면 여기에 표시됩니다</p>
    </div>
  )
}
