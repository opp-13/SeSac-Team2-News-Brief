import { useState, useRef, useEffect } from "react"

interface Props {
  isLoggedIn: boolean
  isAdmin: boolean
  navigate: (path: string) => void
  onLogout: () => void
}

export function Header({ isLoggedIn, isAdmin, navigate, onLogout }: Props) {
  const [profileOpen, setProfileOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  return (
    <header
      className="sticky top-0 z-40 bg-white border-b border-slate-200 h-14"
      style={{ height: 56 }}
    >
      <div className="flex items-center justify-between h-full px-4 max-w-none">
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2 select-none"
          aria-label="홈으로"
        >
          <span
            className="text-slate-900 font-semibold tracking-tight"
            style={{ fontSize: 16, letterSpacing: "-0.01em" }}
          >
            NewsBrief
          </span>
        </button>

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
            >
              {isLoggedIn ? (
                <span className="w-7 h-7 rounded-full bg-cyan-100 text-cyan-800 flex items-center justify-center text-xs font-medium">
                  나
                </span>
              ) : (
                <ProfileIcon />
              )}
            </button>

            {profileOpen && (
              <div className="absolute right-0 top-10 w-44 bg-white border border-slate-200 rounded-lg shadow-sm py-1 z-50">
                {isLoggedIn ? (
                  <>
                    <button
                      onClick={() => {
                        setProfileOpen(false)
                        navigate("/settings")
                      }}
                      className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                    >
                      관심 태그 설정
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => {
                          setProfileOpen(false)
                          navigate("/admin/pipeline")
                        }}
                        className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                      >
                        관리자
                      </button>
                    )}
                    <div className="border-t border-slate-100 my-1" />
                    <button
                      onClick={() => {
                        setProfileOpen(false)
                        onLogout()
                      }}
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
                        navigate("/login")
                      }}
                      className="w-full text-left px-4 py-2 text-[14px] text-slate-700 hover:bg-slate-50"
                    >
                      로그인
                    </button>
                    <button
                      onClick={() => {
                        setProfileOpen(false)
                        navigate("/signup")
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
