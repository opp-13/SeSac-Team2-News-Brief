import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useLogout } from '../../hooks/useLogout'
import { useDeployInfo } from '../../hooks/useDeployInfo'
import { FRONTEND_VERSION } from '../../utils/buildInfo'
import { colors, typeScale } from '../../constants/theme'

// docs/figma-export/components/Header.tsx 이식. §2 표: navigate/isLoggedIn/isAdmin/onLogout
// prop을 전부 훅으로 대체(useNavigate/useAuth/useLogout), named export → default export.
//
// CI/CD 배포 검증용 버전 표시(Front/API)를 이 헤더 안에 얹었다 — 새 sticky 영역을
// 추가하지 않고 기존 헤더(56px, sticky)를 그대로 쓰기 위함. 모바일은 폭이 좁아
// 로고/아이콘만 남기고 버전 표시는 데스크톱(md 이상)에서만 보인다.
export default function Header() {
  const navigate = useNavigate()
  const { isLoggedIn, isAdmin, isLoading } = useAuth()
  const logoutMutation = useLogout()
  const { data: deployInfo, isLoading: isDeployInfoLoading } = useDeployInfo()
  const [profileOpen, setProfileOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleLogout = () => {
    setProfileOpen(false)
    logoutMutation.mutate(undefined, { onSuccess: () => navigate('/') })
  }

  return (
    <header
      className="sticky top-0 z-40 bg-white border-b border-slate-200 h-14"
      style={{ height: 56 }}
    >
      <div className="flex items-center justify-between h-full px-4 max-w-none">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 select-none"
          aria-label="홈으로"
        >
          <span
            className="text-slate-900 font-semibold tracking-tight"
            style={{
              fontSize: typeScale.headline.fontSize,
              letterSpacing: typeScale.headline.letterSpacing,
            }}
          >
            NewsBrief
          </span>
        </button>

        <span
          className="hidden md:inline-flex items-center gap-2"
          style={{
            color: colors.muted,
            fontSize: typeScale.micro.fontSize,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          }}
        >
          Front {FRONTEND_VERSION} · API{' '}
          {isDeployInfoLoading ? '조회 중…' : (deployInfo?.apiVersion ?? '알 수 없음')}
        </span>

        <div className="flex items-center gap-1">
          <button
            className="w-9 h-9 flex items-center justify-center rounded-lg text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors"
            aria-label="검색"
            title="검색 (준비 중)"
          >
            <SearchIcon />
          </button>

          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setProfileOpen((v) => !v)}
              className="w-9 h-9 flex items-center justify-center rounded-lg text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors"
              aria-label="프로필"
              aria-expanded={profileOpen}
              disabled={isLoading}
            >
              {isLoading ? (
                // 세션 조회 중엔 게스트/로그인 아이콘을 확정하지 않는다 (깜빡임 방지).
                <span className="w-7 h-7 rounded-full bg-slate-100 animate-pulse" />
              ) : isLoggedIn ? (
                <span className="w-7 h-7 rounded-full bg-cyan-100 text-cyan-800 flex items-center justify-center text-xs font-medium">
                  나
                </span>
              ) : (
                <ProfileIcon />
              )}
            </button>

            {profileOpen && !isLoading && (
              <div className="absolute right-0 top-10 w-44 bg-white border border-slate-200 rounded-lg shadow-sm py-1 z-50">
                {isLoggedIn ? (
                  <>
                    <button
                      onClick={() => {
                        setProfileOpen(false)
                        navigate('/settings')
                      }}
                      className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                    >
                      관심 태그 설정
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => {
                          setProfileOpen(false)
                          navigate('/admin/pipeline')
                        }}
                        className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                      >
                        관리자
                      </button>
                    )}
                    <div className="border-t border-slate-100 my-1" />
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                    >
                      로그아웃
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => {
                        setProfileOpen(false)
                        navigate('/login')
                      }}
                      className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                    >
                      로그인
                    </button>
                    <button
                      onClick={() => {
                        setProfileOpen(false)
                        navigate('/signup')
                      }}
                      className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                    >
                      회원가입
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

function SearchIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function ProfileIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}
