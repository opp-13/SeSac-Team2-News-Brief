import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSignup } from '../../hooks/useSignup'
import { useTags } from '../../hooks/useTags'
import { colors, typeScale, radius } from '../../constants/theme'
import { errorMessage } from '../../utils/apiError'

// docs/figma-export/pages/SignupPage.tsx 이식.
//
// §2 표 적용: navigate/onLogin prop → useNavigate()/useSignup()(TanStack Query,
// hooks/useSignup.ts — LoginPage의 useLogin과 같은 패턴), 선택 가능한 태그는 서버(useTags)에서 받는다. SettingsPage
// 때 옮긴 constants/tags.ts를 재사용, named export → default export, 하드코딩 색상 →
// theme.ts 토큰(정확히 일치하는 것만).
//
// 원본은 2단계에서 고른 selectedTags를 onLogin()에 전혀 넘기지 않았다 — 그러면 태그
// 선택 단계가 화면만 있고 실제로는 아무 효과가 없다. useSignup 뮤테이션에 함께 보내서
// 가입 직후 관심 태그가 실제로 반영되게 했다(원본 동작을 바꾼 부분이라 알려드린다).
export default function SignupPage() {
  const navigate = useNavigate()
  const signupMutation = useSignup()
  const { data: allTags = [] } = useTags()

  const [step, setStep] = useState<1 | 2>(1)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // users.nickname은 NOT NULL이고 백엔드 SignupRequest의 필수 필드다.
  // 받지 않으면 회원가입이 422로 실패한다.
  const [nickname, setNickname] = useState('')
  const [selectedTags, setSelectedTags] = useState<string[]>([])

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]))
  }

  const handleStep1 = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (email && nickname.trim() && password.length >= 8) setStep(2)
  }

  const handleFinish = () => {
    signupMutation.mutate(
      { email, password, nickname: nickname.trim(), userTags: selectedTags },
      { onSuccess: () => navigate('/') },
    )
  }

  // 가입 실패(이메일 중복 등)를 화면에 띄운다. 이전에는 실패해도 아무 표시가 없어서
  // 버튼만 되돌아왔다 — 서버는 409 EMAIL_ALREADY_EXISTS를 내려주고 있었다.
  const error = errorMessage(
    signupMutation.error,
    '회원가입에 실패했습니다. 네트워크 상태를 확인해주세요.',
  )
  const loading = signupMutation.isPending

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
                  background: step >= s ? colors.accent : colors.border,
                  color: step >= s ? colors.surface : colors.muted,
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
              <h1
                className="text-slate-900 font-semibold mb-1"
                style={{ fontSize: typeScale.h2.fontSize, letterSpacing: typeScale.h2.letterSpacing }}
              >
                계정 만들기
              </h1>
              <p className="text-slate-500 mb-6" style={{ fontSize: typeScale.caption.fontSize }}>
                1단계: 기본 정보
              </p>

              <form onSubmit={handleStep1} className="space-y-4">
                <div>
                  <label
                    className="block text-slate-700 mb-1.5"
                    style={{ fontSize: 14, fontWeight: 500 }}
                  >
                    이메일
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="hello@example.com"
                    className="w-full h-10 px-3 rounded-lg border border-slate-200 text-slate-900 placeholder-slate-400 outline-none focus:border-cyan-800 focus:ring-1 focus:ring-cyan-800 transition-colors"
                    style={{ fontSize: 14, borderRadius: radius.control }}
                    required
                  />
                </div>

                <div>
                  <label
                    className="block text-slate-700 mb-1.5"
                    style={{ fontSize: 14, fontWeight: 500 }}
                  >
                    닉네임
                  </label>
                  <input
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    placeholder="피드에 표시될 이름"
                    maxLength={50}
                    className="w-full h-10 px-3 rounded-lg border border-slate-200 text-slate-900 placeholder-slate-400 outline-none focus:border-cyan-800 focus:ring-1 focus:ring-cyan-800 transition-colors"
                    style={{ fontSize: 14, borderRadius: radius.control }}
                    required
                  />
                </div>

                <div>
                  <label
                    className="block text-slate-700 mb-1.5"
                    style={{ fontSize: 14, fontWeight: 500 }}
                  >
                    비밀번호
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="8자 이상"
                    minLength={8}
                    className="w-full h-10 px-3 rounded-lg border border-slate-200 text-slate-900 placeholder-slate-400 outline-none focus:border-cyan-800 focus:ring-1 focus:ring-cyan-800 transition-colors"
                    style={{ fontSize: 14, borderRadius: radius.control }}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="w-full h-10 rounded-lg text-white font-medium"
                  style={{ background: colors.accent, fontSize: 14, borderRadius: radius.control }}
                >
                  다음
                </button>
              </form>
            </>
          ) : (
            <>
              <h1
                className="text-slate-900 font-semibold mb-1"
                style={{ fontSize: typeScale.h2.fontSize, letterSpacing: typeScale.h2.letterSpacing }}
              >
                관심 태그 선택
              </h1>
              <p className="text-slate-500 mb-6" style={{ fontSize: typeScale.caption.fontSize }}>
                2단계: 관심 있는 주제를 골라주세요 (복수 선택 가능)
              </p>

              <div className="flex flex-wrap gap-2 mb-6">
                {allTags.map(({ name: tag }) => (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className="h-8 px-3 transition-colors"
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      borderRadius: radius.chip,
                      background: selectedTags.includes(tag) ? colors.primary : colors.surface,
                      color: selectedTags.includes(tag) ? colors.surface : colors.neutral.text,
                      border: selectedTags.includes(tag) ? 'none' : `1px solid ${colors.border}`,
                    }}
                  >
                    {tag}
                  </button>
                ))}
              </div>

              {selectedTags.length === 0 && (
                <p className="text-slate-400 text-[13px] mb-4">나중에 설정에서 변경할 수 있어요</p>
              )}

              {error && (
                <p
                  role="alert"
                  className="text-[13px] mb-3"
                  style={{ color: colors.status.error.text }}
                >
                  {error}
                </p>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => setStep(1)}
                  className="h-10 px-4 rounded-lg border border-slate-200 text-slate-700 text-[14px]"
                  style={{ borderRadius: radius.control }}
                >
                  이전
                </button>
                <button
                  onClick={handleFinish}
                  disabled={loading}
                  className="flex-1 h-10 rounded-lg text-white font-medium disabled:opacity-60"
                  style={{ background: colors.accent, fontSize: 14, borderRadius: radius.control }}
                >
                  {loading ? '가입 중…' : '가입 완료'}
                </button>
              </div>
            </>
          )}
        </div>

        <p className="text-center text-slate-500 mt-4" style={{ fontSize: typeScale.caption.fontSize }}>
          이미 계정이 있으신가요?{' '}
          <button onClick={() => navigate('/login')} className="text-cyan-800 hover:underline">
            로그인
          </button>
        </p>
      </div>
    </div>
  )
}
