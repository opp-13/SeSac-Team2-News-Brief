import { useState } from 'react'
import { ALL_TAGS } from '../data/mockData'

interface Props {
  navigate: (path: string) => void
  onLogin: () => void
}

export function SignupPage({ navigate, onLogin }: Props) {
  const [step, setStep] = useState<1 | 2>(1)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    )
  }

  const handleStep1 = (e: React.FormEvent) => {
    e.preventDefault()
    if (email && password.length >= 8) setStep(2)
  }

  const handleFinish = () => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      onLogin()
    }, 800)
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full" style={{ maxWidth: 440 }}>
        {/* Logo */}
        <div className="text-center mb-8">
          <button
            onClick={() => navigate('/')}
            className="text-slate-900 font-semibold"
            style={{ fontSize: 20, letterSpacing: '-0.01em' }}
          >
            뉴스레이더
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6 justify-center">
          {[1, 2].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium"
                style={{
                  background: step >= s ? '#155E75' : '#E2E8F0',
                  color: step >= s ? '#fff' : '#94A3B8',
                }}
              >
                {s}
              </div>
              {s < 2 && <div className="w-8 h-px bg-slate-200" />}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-8">
          {step === 1 ? (
            <>
              <h1 className="text-slate-900 font-semibold mb-1" style={{ fontSize: 18, letterSpacing: '-0.01em' }}>
                계정 만들기
              </h1>
              <p className="text-slate-500 mb-6" style={{ fontSize: 13 }}>
                1단계: 기본 정보
              </p>

              <form onSubmit={handleStep1} className="space-y-4">
                <div>
                  <label className="block text-slate-700 mb-1.5" style={{ fontSize: 14, fontWeight: 500 }}>
                    이메일
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="hello@example.com"
                    className="w-full h-10 px-3 rounded-lg border border-slate-200 text-slate-900 placeholder-slate-400 outline-none focus:border-cyan-800 focus:ring-1 focus:ring-cyan-800 transition-colors"
                    style={{ fontSize: 14, borderRadius: 8 }}
                    required
                  />
                </div>

                <div>
                  <label className="block text-slate-700 mb-1.5" style={{ fontSize: 14, fontWeight: 500 }}>
                    비밀번호
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="8자 이상"
                    minLength={8}
                    className="w-full h-10 px-3 rounded-lg border border-slate-200 text-slate-900 placeholder-slate-400 outline-none focus:border-cyan-800 focus:ring-1 focus:ring-cyan-800 transition-colors"
                    style={{ fontSize: 14, borderRadius: 8 }}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="w-full h-10 rounded-lg text-white font-medium"
                  style={{ background: '#155E75', fontSize: 14, borderRadius: 8 }}
                >
                  다음
                </button>
              </form>
            </>
          ) : (
            <>
              <h1 className="text-slate-900 font-semibold mb-1" style={{ fontSize: 18, letterSpacing: '-0.01em' }}>
                관심 태그 선택
              </h1>
              <p className="text-slate-500 mb-6" style={{ fontSize: 13 }}>
                2단계: 관심 있는 주제를 골라주세요 (복수 선택 가능)
              </p>

              <div className="flex flex-wrap gap-2 mb-6">
                {ALL_TAGS.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className="h-8 px-3 transition-colors"
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      borderRadius: 6,
                      background: selectedTags.includes(tag) ? '#0F172A' : '#FFFFFF',
                      color: selectedTags.includes(tag) ? '#FFFFFF' : '#334155',
                      border: selectedTags.includes(tag) ? 'none' : '1px solid #E2E8F0',
                    }}
                  >
                    {tag}
                  </button>
                ))}
              </div>

              {selectedTags.length === 0 && (
                <p className="text-slate-400 text-[13px] mb-4">
                  나중에 설정에서 변경할 수 있어요
                </p>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => setStep(1)}
                  className="h-10 px-4 rounded-lg border border-slate-200 text-slate-700 text-[14px]"
                  style={{ borderRadius: 8 }}
                >
                  이전
                </button>
                <button
                  onClick={handleFinish}
                  disabled={loading}
                  className="flex-1 h-10 rounded-lg text-white font-medium disabled:opacity-60"
                  style={{ background: '#155E75', fontSize: 14, borderRadius: 8 }}
                >
                  {loading ? '가입 중…' : '가입 완료'}
                </button>
              </div>
            </>
          )}
        </div>

        <p className="text-center text-slate-500 mt-4" style={{ fontSize: 13 }}>
          이미 계정이 있으신가요?{' '}
          <button onClick={() => navigate('/login')} className="text-cyan-800 hover:underline">
            로그인
          </button>
        </p>
      </div>
    </div>
  )
}
