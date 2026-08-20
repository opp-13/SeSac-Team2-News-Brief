import { useState } from 'react'
import { ALL_TAGS } from '../data/mockData'

interface Props {
  isLoggedIn: boolean
  userTags: string[]
  onSaveTags: (tags: string[]) => void
  navigate: (path: string) => void
}

export function SettingsPage({ isLoggedIn, userTags, onSaveTags, navigate }: Props) {
  const [selected, setSelected] = useState<string[]>(userTags)
  const [saved, setSaved] = useState(false)

  if (!isLoggedIn) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-slate-700 text-[15px]">로그인이 필요한 페이지입니다</p>
        <button
          onClick={() => navigate('/login')}
          className="h-10 px-4 rounded-lg text-white text-[14px] font-medium"
          style={{ background: '#155E75', borderRadius: 8 }}
        >
          로그인
        </button>
      </div>
    )
  }

  const toggle = (tag: string) => {
    setSaved(false)
    setSelected((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    )
  }

  const handleSave = () => {
    onSaveTags(selected)
    setSaved(true)
  }

  return (
    <div className="mx-auto py-8 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
      <h1
        className="text-slate-900 font-semibold mb-1"
        style={{ fontSize: 22, letterSpacing: '-0.01em' }}
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
                borderRadius: 6,
                background: selected.includes(tag) ? '#0F172A' : '#FFFFFF',
                color: selected.includes(tag) ? '#FFFFFF' : '#334155',
                border: selected.includes(tag) ? 'none' : '1px solid #E2E8F0',
              }}
            >
              {tag}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            className="h-10 px-4 rounded-lg text-white font-medium"
            style={{ background: '#155E75', fontSize: 14, borderRadius: 8 }}
          >
            저장
          </button>
          {saved && (
            <span className="text-[13px]" style={{ color: '#166534' }}>
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
