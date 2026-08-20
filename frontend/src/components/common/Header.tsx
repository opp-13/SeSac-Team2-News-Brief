import { useState, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useLogout } from '../../hooks/useLogout'
import { useDeployInfo } from '../../hooks/useDeployInfo'
import { FRONTEND_VERSION } from '../../utils/buildInfo'
import { colors, typeScale, radius, spacing } from '../../constants/theme'

const MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace'

// docs/figma-export/components/Header.tsx 이식. §2 표: navigate/isLoggedIn/isAdmin/onLogout
// prop을 전부 훅으로 대체(useNavigate/useAuth/useLogout), named export → default export.
//
// 레이아웃은 3열이다 — [로고] [검색 입력창(중앙)] [버전 칩 + 로그인/프로필].
// 양쪽 열에 flex-1을 주어 가운데 입력창이 헤더 정중앙에 오도록 했다(절대 위치를 쓰면
// 좁은 폭에서 로고·버튼과 겹친다). 높이는 기존 56px 그대로 — design_plan §4의
// "상단 고정 영역 최대 2단, 합계 120px 이하"를 넘기지 않기 위해 단을 추가하지 않는다.
export default function Header() {
  const navigate = useNavigate()
  const { isLoggedIn, isAdmin, isLoading } = useAuth()
  const logoutMutation = useLogout()
  const { data: deployInfo, isLoading: isDeployInfoLoading, isError: isDeployInfoError } =
    useDeployInfo()
  const [profileOpen, setProfileOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // 검색어의 진실은 URL(`/?q=`)이다. 입력창은 편집 중인 값만 로컬로 들고 있고,
  // URL이 밖에서 바뀌면(목록의 "검색 초기화", 뒤로가기 등) 렌더 중 상태 조정으로 되맞춘다
  // — 이펙트 안에서 setState하면 react-hooks/set-state-in-effect에 걸린다.
  const [searchParams] = useSearchParams()
  const urlQuery = searchParams.get('q') ?? ''
  const [inputValue, setInputValue] = useState(urlQuery)
  const [prevUrlQuery, setPrevUrlQuery] = useState(urlQuery)
  if (prevUrlQuery !== urlQuery) {
    setPrevUrlQuery(urlQuery)
    setInputValue(urlQuery)
  }

  const [searchFocused, setSearchFocused] = useState(false)

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

  // 어느 화면에서 검색하든 목록으로 이동한다. 빈 문자열이면 q를 아예 붙이지 않아
  // "검색 안 한 상태"와 "빈 검색어"가 같은 URL이 되게 한다.
  const submitSearch = (raw: string) => {
    const q = raw.trim()
    navigate(q ? `/?q=${encodeURIComponent(q)}` : '/')
  }

  const apiVersionLabel = isDeployInfoLoading
    ? '…'
    : isDeployInfoError || !deployInfo
      ? '—'
      : deployInfo.apiVersion

  return (
    <header
      className="sticky top-0 z-40 bg-white border-b border-slate-200"
      style={{ height: 56 }}
    >
      <div className="flex items-center h-full px-4" style={{ gap: spacing.md }}>
        {/* 좌: 로고 */}
        <div className="flex-1 flex items-center min-w-0">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 select-none shrink-0"
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
        </div>

        {/* 중앙: 검색 입력창. Enter로 제출한다 (돋보기는 장식이므로 button이 아니다 —
            design_plan §4 "아이콘만 있고 라벨 없는 버튼 금지"). */}
        <form
          role="search"
          onSubmit={(e) => {
            e.preventDefault()
            submitSearch(inputValue)
          }}
          className="hidden sm:block shrink-0 w-full"
          style={{ maxWidth: 400 }}
        >
          <div
            className="flex items-center"
            style={{
              height: 36,
              gap: spacing.sm,
              padding: `0 ${spacing.md}px`,
              background: colors.surfaceAlt,
              border: `1px solid ${searchFocused ? colors.accent : colors.border}`,
              outline: searchFocused ? `1px solid ${colors.accent}` : 'none',
              borderRadius: radius.control,
            }}
          >
            <span className="shrink-0" style={{ color: colors.muted }} aria-hidden="true">
              <SearchIcon />
            </span>
            <input
              type="search"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              placeholder="기사 제목·출처 검색"
              aria-label="기사 검색"
              className="flex-1 min-w-0 bg-transparent border-0 outline-none"
              style={{
                fontSize: typeScale.caption.fontSize,
                color: colors.primary,
              }}
            />
            {inputValue && (
              <button
                type="button"
                onClick={() => {
                  setInputValue('')
                  if (urlQuery) navigate('/')
                }}
                className="shrink-0 flex items-center justify-center"
                style={{ color: colors.muted, width: 20, height: 20 }}
                aria-label="검색어 지우기"
                title="검색어 지우기"
              >
                <ClearIcon />
              </button>
            )}
          </div>
        </form>

        {/* 우: 버전 칩 + 로그인/프로필 */}
        <div className="flex-1 flex items-center justify-end min-w-0" style={{ gap: spacing.sm }}>
          <VersionChip frontend={FRONTEND_VERSION} api={apiVersionLabel} />

          {isLoading ? (
            // 세션 조회 중엔 게스트/로그인 UI를 확정하지 않는다 (깜빡임 방지).
            <span
              className="animate-pulse shrink-0"
              style={{ width: 72, height: 36, borderRadius: radius.control, background: colors.neutral.bg }}
            />
          ) : isLoggedIn ? (
            <div className="relative shrink-0" ref={menuRef}>
              <button
                onClick={() => setProfileOpen((v) => !v)}
                className="w-9 h-9 flex items-center justify-center rounded-lg text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                aria-label="내 계정 메뉴"
                aria-expanded={profileOpen}
              >
                <span
                  className="w-7 h-7 rounded-full flex items-center justify-center"
                  style={{
                    background: colors.accentTint,
                    color: colors.accent,
                    fontSize: typeScale.micro.fontSize,
                    fontWeight: 500,
                  }}
                >
                  나
                </span>
              </button>

              {profileOpen && (
                <div className="absolute right-0 top-10 w-44 bg-white border border-slate-200 rounded-lg py-1 z-50">
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
                </div>
              )}
            </div>
          ) : (
            // 비로그인: 아이콘 + 드롭다운이 아니라 라벨이 붙은 로그인 버튼을 바로 노출한다.
            // 회원가입은 LoginPage 하단 링크로 이어진다 — design_plan §4
            // "한 화면에 Primary 버튼은 하나만"을 지키려고 헤더에 두 개를 두지 않았다.
            <button
              onClick={() => navigate('/login')}
              className="shrink-0 flex items-center"
              style={{
                height: 36,
                gap: spacing.xs,
                padding: `0 ${spacing.md}px`,
                background: colors.accent,
                color: colors.surface,
                borderRadius: radius.control,
                fontSize: typeScale.caption.fontSize,
                fontWeight: 500,
              }}
            >
              <LoginIcon />
              로그인
            </button>
          )}
        </div>
      </div>
    </header>
  )
}

// CI/CD 배포 검증용 버전 표시. 값(버전 문자열)만 시그니처 시안(colors.accent)으로 강조하고
// 라벨은 보조색으로 눌러 둔다. 배경은 accentTint(#CFFAFE)를 쓰지 않았다 — 그 톤은 기사 행의
// 태그 칩과 AI 요약 라벨이 이미 쓰고 있어서, 버전 칩까지 같은 톤이면 태그처럼 읽힌다.
function VersionChip({ frontend, api }: { frontend: string; api: string }) {
  return (
    <span
      className="hidden md:inline-flex items-center shrink-0"
      style={{
        gap: spacing.xs,
        padding: `${spacing.xs}px ${spacing.sm}px`,
        background: colors.surfaceAlt,
        border: `1px solid ${colors.border}`,
        borderRadius: radius.chip,
        fontSize: typeScale.micro.fontSize,
        fontFamily: MONO,
        lineHeight: 1,
      }}
      title={`프론트엔드 ${frontend} / API ${api}`}
    >
      <span style={{ color: colors.muted }}>Front</span>
      <span style={{ color: colors.accent, fontWeight: 500 }}>{frontend}</span>
      <span aria-hidden="true" style={{ color: colors.border }}>
        |
      </span>
      <span style={{ color: colors.muted }}>API</span>
      <span style={{ color: colors.accent, fontWeight: 500 }}>{api}</span>
    </span>
  )
}

function SearchIcon() {
  return (
    <svg
      width="16"
      height="16"
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

function ClearIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function LoginIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <polyline points="10 17 15 12 10 7" />
      <line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  )
}
