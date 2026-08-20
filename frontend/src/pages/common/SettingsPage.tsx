import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useSaveUserTags } from '../../hooks/useSaveUserTags'
import { ALL_TAGS } from '../../constants/tags'
import { colors, typeScale, radius } from '../../constants/theme'

// docs/figma-export/pages/SettingsPage.tsx 이식.
//
// §2 표 적용: navigate prop → useNavigate(), isLoggedIn/userTags prop → useAuth(),
// onSaveTags prop → useSaveUserTags()(TanStack Query, hooks/useSaveUserTags.ts —
// auth 세션 캐시의 userTags 필드를 갱신), named export → default export,
// 하드코딩 색상 → theme.ts 토큰(정확히 일치하는 것만).
//
// ALL_TAGS(선택 가능한 전체 태그 목록)는 서버 데이터가 아니라 고정 상수라
// TanStack Query 대상이 아니라고 판단했다 — constants/tags.ts 참고.
//
// 세션 로딩 중엔 "로그인이 필요합니다"를 성급하게 보여주지 않는다 — 실제로는
// 로그인 상태인데 세션 조회가 아직 안 끝났을 때 잘못된 화면이 잠깐 보이는 걸
// 막기 위함(NewsFeedPage와 같은 이유).
export default function SettingsPage() {
  const navigate = useNavigate()
  const { user, isLoggedIn, isLoading: isSessionLoading } = useAuth()
  const saveMutation = useSaveUserTags()

  const [selected, setSelected] = useState<string[]>([])
  const [hasSeeded, setHasSeeded] = useState(false)
  const [saved, setSaved] = useState(false)

  // 세션이 로드되면 사용자의 현재 관심 태그로 딱 한 번만 시드한다 — RetentionPage와
  // 같은 이유로, 이후 백그라운드 재검증이 편집 중인 선택을 덮어쓰지 않게 한다.
  if (user && !hasSeeded) {
    setHasSeeded(true)
    setSelected(user.userTags)
  }

  if (isSessionLoading) {
    return <SettingsSkeleton />
  }

  if (!isLoggedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-slate-700 text-[15px]">로그인이 필요한 페이지입니다</p>
        <button
          onClick={() => navigate('/login')}
          className="h-10 px-4 rounded-lg text-white text-[14px] font-medium"
          style={{ background: colors.accent, borderRadius: radius.control }}
        >
          로그인
        </button>
      </div>
    )
  }

  const toggle = (tag: string) => {
    setSaved(false)
    setSelected((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]))
  }

  const handleSave = () => {
    saveMutation.mutate(selected, { onSuccess: () => setSaved(true) })
  }

  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
      <h1
        className="text-slate-900 font-semibold mb-1"
        style={{ fontSize: typeScale.h1.fontSize, letterSpacing: typeScale.h1.letterSpacing }}
      >
        관심 태그 설정
      </h1>
      <p className="text-slate-500 mb-8" style={{ fontSize: 14 }}>
        선택한 태그에 맞는 기사를 우선 노출합니다
      </p>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-slate-900 font-semibold mb-4" style={{ fontSize: 15 }}>
          관심 주제
        </h2>

        <div className="flex flex-wrap gap-2 mb-6">
          {ALL_TAGS.map((tag) => (
            <button
              key={tag}
              onClick={() => toggle(tag)}
              className="h-8 px-3 transition-colors"
              style={{
                fontSize: 13,
                fontWeight: 500,
                borderRadius: radius.chip,
                background: selected.includes(tag) ? colors.primary : colors.surface,
                color: selected.includes(tag) ? colors.surface : colors.neutral.text,
                border: selected.includes(tag) ? 'none' : `1px solid ${colors.border}`,
              }}
            >
              {tag}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="h-10 px-4 rounded-lg text-white font-medium disabled:opacity-60"
            style={{ background: colors.accent, fontSize: 14, borderRadius: radius.control }}
          >
            {saveMutation.isPending ? '저장 중…' : '저장'}
          </button>
          {saved && (
            <span className="text-[13px]" style={{ color: colors.status.success.text }}>
              저장되었습니다
            </span>
          )}
        </div>
      </div>

      {selected.length === 0 && (
        <p className="text-slate-400 text-[13px] mt-3">
          태그를 선택하지 않으면 전체 최신 뉴스를 보여줍니다
        </p>
      )}
    </div>
  )
}

function SettingsSkeleton() {
  return (
    <div className="mx-auto py-8 px-4 animate-pulse" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
      <div className="h-6 w-32 rounded bg-slate-100 mb-2" />
      <div className="h-4 w-56 rounded bg-slate-100 mb-8" />
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="h-4 w-20 rounded bg-slate-100 mb-4" />
        <div className="flex flex-wrap gap-2 mb-6">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="h-8 w-16 rounded-md bg-slate-100" />
          ))}
        </div>
        <div className="h-10 w-20 rounded-lg bg-slate-100" />
      </div>
    </div>
  )
}
