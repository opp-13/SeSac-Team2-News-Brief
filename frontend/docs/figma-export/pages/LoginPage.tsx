import { useState } from 'react'

interface Props {
  navigate: (path: string) => void
  onLogin: (asAdmin?: boolean) => void
}

export function LoginPage({ navigate, onLogin }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!email || !password) {
      setError('이메일과 비밀번호를 입력해주세요.')
      return
    }
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      const asAdmin = email.includes('admin')
      onLogin(asAdmin)
    }, 800)
  }

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
          <h1 className="text-slate-900 font-semibold mb-6" style={{ fontSize: 18, letterSpacing: '-0.01em' }}>
            로그인
          </h1>

          <form onSubmit={handleSubmit} className="space-y-4">
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
                autoComplete="email"
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
                placeholder="••••••••"
                className="w-full h-10 px-3 rounded-lg border border-slate-200 text-slate-900 placeholder-slate-400 outline-none focus:border-cyan-800 focus:ring-1 focus:ring-cyan-800 transition-colors"
                style={{ fontSize: 14, borderRadius: 8 }}
                autoComplete="current-password"
              />
            </div>

            {error && (
              <p className="text-red-700 text-[13px]">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-10 rounded-lg text-white font-medium transition-opacity disabled:opacity-60"
              style={{ background: '#155E75', fontSize: 14, borderRadius: 8 }}
            >
              {loading ? '로그인 중…' : '로그인'}
            </button>
          </form>

          <p className="text-center text-slate-500 mt-5" style={{ fontSize: 13 }}>
            계정이 없으신가요?{' '}
            <button
              onClick={() => navigate('/signup')}
              className="text-cyan-800 hover:underline"
            >
              회원가입
            </button>
          </p>

          <p className="text-center text-slate-400 mt-2" style={{ fontSize: 12 }}>
            관리자 계정: admin@example.com
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
