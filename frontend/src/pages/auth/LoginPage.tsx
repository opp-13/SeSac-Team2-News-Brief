import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLogin } from '../../hooks/useLogin'
import { colors, typeScale, radius } from '../../constants/theme'

export default function LoginPage() {
  const navigate = useNavigate()
  const loginMutation = useLogin()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [validationError, setValidationError] = useState('')

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setValidationError('')
    if (!email || !password) {
      setValidationError('이메일과 비밀번호를 입력해주세요.')
      return
    }
    loginMutation.mutate(
      { email, password },
      { onSuccess: () => navigate('/') },
    )
  }

  const error = validationError
  const loading = loginMutation.isPending

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full" style={{ maxWidth: 400 }}>
        {/* Logo */}
        <div className="text-center mb-8">
          <button
            onClick={() => navigate('/')}
            className="text-slate-900 font-semibold"
            style={{ fontSize: 20, letterSpacing: '-0.01em' }}
          >
            뉴스레이더
          </button>
          <p className="text-slate-500 mt-1" style={{ fontSize: 14 }}>
            AI가 요약한 뉴스를 내 관심사에 맞게
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-8">
          <h1
            className="text-slate-900 font-semibold mb-6"
            style={{ fontSize: typeScale.h2.fontSize, letterSpacing: typeScale.h2.letterSpacing }}
          >
            로그인
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
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
                autoComplete="email"
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
                placeholder="••••••••"
                className="w-full h-10 px-3 rounded-lg border border-slate-200 text-slate-900 placeholder-slate-400 outline-none focus:border-cyan-800 focus:ring-1 focus:ring-cyan-800 transition-colors"
                style={{ fontSize: 14, borderRadius: radius.control }}
                autoComplete="current-password"
              />
            </div>

            {error && (
              <p className="text-[13px]" style={{ color: colors.status.error.text }}>
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-10 rounded-lg text-white font-medium transition-opacity disabled:opacity-60"
              style={{ background: colors.accent, fontSize: 14, borderRadius: radius.control }}
            >
              {loading ? '로그인 중…' : '로그인'}
            </button>
          </form>

          <p className="text-center text-slate-500 mt-5" style={{ fontSize: 13 }}>
            계정이 없으신가요?{' '}
            <button onClick={() => navigate('/signup')} className="text-cyan-800 hover:underline">
              회원가입
            </button>
          </p>
        </div>

        <button
          onClick={() => navigate('/')}
          className="block text-center w-full mt-4 text-slate-500 hover:text-slate-700"
          style={{ fontSize: 13 }}
        >
          로그인 없이 둘러보기
        </button>
      </div>
    </div>
  )
}
