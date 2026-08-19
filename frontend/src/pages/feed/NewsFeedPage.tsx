import { useRef, useState, forwardRef, type RefObject } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import type { Article } from '../../types/feed'
import { mockArticles } from '../../mocks/feedMockData'
import { useAuth } from '../../hooks/useAuth'
import { useFeed } from '../../hooks/useFeed'
import { colors, typeScale, radius, spacing } from '../../constants/theme'
import ArticleModal from '../../components/feed/ArticleModal'

const GUEST_CATEGORIES = ['전체', 'IT', '경제', '정치', '글로벌', '스타트업', '보안']

// "/"와 "/articles/:id" 둘 다 이 컴포넌트로 연결된다(routes/AppRoutes.tsx). 목록과
// 모달을 같은 컴포넌트가 다루므로 openArticleId는 prop이 아니라 라우트 파라미터에서
// 직접 읽는다 — 열기/닫기는 navigate()로, 상세 URL은 useParams로 확인한다.
export default function NewsFeedPage() {
  const { id: paramArticleId } = useParams<{ id: string }>()
  const openArticleId = paramArticleId ?? null
  const { user, isLoggedIn, isLoading: isSessionLoading } = useAuth()
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState('전체')
  const [readIds, setReadIds] = useState<Set<string>>(new Set())
  const [reachedEnd, setReachedEnd] = useState(false)
  const rowRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  const userTags = user?.userTags ?? []
  const filters = isLoggedIn ? ['전체', ...userTags] : GUEST_CATEGORIES

  const {
    data: articles = [],
    isLoading: isFeedLoading,
    isError,
    refetch,
  } = useFeed({ activeFilter, isLoggedIn })

  // 필터가 바뀌면 "끝 도달" 표시를 다시 접는다. 이펙트 대신 렌더 중 상태 조정 패턴을 쓴다
  // (react-hooks/set-state-in-effect — 이펙트 안에서 setState하면 렌더가 한 번 더 캐스케이드된다).
  const [prevActiveFilter, setPrevActiveFilter] = useState(activeFilter)
  if (prevActiveFilter !== activeFilter) {
    setPrevActiveFilter(activeFilter)
    setReachedEnd(false)
  }

  const openArticle = mockArticles.find((a) => a.id === openArticleId) ?? null

  const handleOpenArticle = (id: string) => {
    setReadIds((prev) => new Set([...prev, id]))
    navigate(`/articles/${id}`)
  }

  const handleCloseArticle = () => {
    navigate('/')
    if (openArticleId) {
      setTimeout(() => rowRefs.current[openArticleId]?.focus(), 50)
    }
  }

  // 세션 조회가 끝나기 전엔 게스트/로그인 전용 UI(헤딩, 필터칩, 배너)를 확정해서
  // 그리지 않는다 — 로그인 사용자가 게스트 화면을 봤다가 바뀌는 깜빡임을 막는다.
  if (isSessionLoading) {
    return <NewsFeedPageSkeleton />
  }

  return (
    <>
      <div className="md:pl-0" style={{ paddingLeft: 0 }}>
        {/* Sticky filter bar */}
        <div className="sticky z-30 bg-slate-50 border-b border-slate-200" style={{ top: 56 }}>
          <div className="mx-auto px-4 md:px-6" style={{ maxWidth: 760 + 64 }}>
            <div
              className="flex items-center gap-2 py-3 overflow-x-auto no-scrollbar"
              style={{ paddingLeft: 64 }}
            >
              {filters.map((filter) => (
                <button
                  key={filter}
                  onClick={() => setActiveFilter(filter)}
                  className="shrink-0 h-8 px-3 rounded-md text-sm transition-colors"
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    borderRadius: radius.chip,
                    background: activeFilter === filter ? colors.primary : colors.surface,
                    color: activeFilter === filter ? colors.surface : colors.neutral.text,
                    border: activeFilter === filter ? 'none' : `1px solid ${colors.border}`,
                  }}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="mx-auto py-6 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
          {/* Page heading */}
          <h1
            className="text-slate-900 font-semibold mb-4"
            style={{ fontSize: typeScale.h1.fontSize, letterSpacing: typeScale.h1.letterSpacing }}
          >
            {isLoggedIn ? '관심사 기반 뉴스' : '최신 뉴스'}
          </h1>

          {/* Guest login banner */}
          {!isLoggedIn && (
            <div className="flex items-center justify-between px-4 py-3 rounded-xl border border-slate-200 bg-white mb-5">
              <p className="text-slate-700 text-[15px]">
                로그인하고 관심사에 맞는 뉴스를 받아보세요
              </p>
              <button
                onClick={() => navigate('/login')}
                className="h-8 px-3 rounded-lg text-white text-[13px] font-medium shrink-0"
                style={{ background: colors.accent, borderRadius: radius.control }}
              >
                로그인
              </button>
            </div>
          )}

          {/* Feed states */}
          {isFeedLoading && <SkeletonFeed />}

          {isError && <ErrorState onRetry={() => refetch()} />}

          {!isFeedLoading && !isError && articles.length === 0 && (
            <EmptyState isLoggedIn={isLoggedIn} navigate={navigate} />
          )}

          {!isFeedLoading && !isError && articles.length > 0 && (
            <>
              <ArticleList
                articles={articles}
                isLoggedIn={isLoggedIn}
                readIds={readIds}
                openArticleId={openArticleId}
                onOpen={handleOpenArticle}
                rowRefs={rowRefs}
              />
              {reachedEnd ? (
                <p className="text-center text-slate-400 text-[13px] py-8">
                  더 이상 기사가 없습니다
                </p>
              ) : (
                <button
                  onClick={() => setReachedEnd(true)}
                  className="w-full text-center text-slate-400 text-[13px] py-6 hover:text-slate-600"
                >
                  더 보기
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {openArticle && (
        <ArticleModal
          article={openArticle}
          allArticles={articles.length > 0 ? articles : mockArticles}
          onClose={handleCloseArticle}
          onNavigate={handleOpenArticle}
        />
      )}
    </>
  )
}

function ArticleList({
  articles,
  isLoggedIn,
  readIds,
  openArticleId,
  onOpen,
  rowRefs,
}: {
  articles: Article[]
  isLoggedIn: boolean
  readIds: Set<string>
  openArticleId: string | null
  onOpen: (id: string) => void
  rowRefs: RefObject<Record<string, HTMLButtonElement | null>>
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200" style={{ borderRadius: radius.card }}>
      {articles.map((article, idx) => {
        const isRead = readIds.has(article.id) || article.isRead
        const isLast = idx === articles.length - 1
        return (
          <ArticleRow
            key={article.id}
            article={article}
            isRead={!!isRead}
            isLast={isLast}
            isLoggedIn={isLoggedIn}
            isActive={openArticleId === article.id}
            onOpen={onOpen}
            ref={(el) => {
              rowRefs.current[article.id] = el
            }}
          />
        )
      })}
    </div>
  )
}

interface RowProps {
  article: Article
  isRead: boolean
  isLast: boolean
  isLoggedIn: boolean
  isActive: boolean
  onOpen: (id: string) => void
}

const ArticleRow = forwardRef<HTMLButtonElement, RowProps>(
  ({ article, isRead, isLast, isLoggedIn, isActive, onOpen }, ref) => {
    return (
      <button
        ref={ref}
        onClick={() => onOpen(article.id)}
        className="w-full text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-800 focus-visible:ring-inset"
        style={{
          display: 'block',
          cursor: 'pointer',
          background: isActive ? colors.surfaceAlt : 'transparent',
          borderBottom: isLast ? 'none' : `1px solid ${colors.border}`,
          padding: '14px 20px',
        }}
        onMouseEnter={(e) => {
          if (!isActive) (e.currentTarget as HTMLElement).style.background = colors.surfaceAlt
        }}
        onMouseLeave={(e) => {
          if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'
        }}
        aria-label={article.headline}
      >
        {/* Meta row */}
        <div className="flex items-center justify-between mb-1.5" style={{ height: 20 }}>
          <div className="flex items-center gap-1.5">
            {article.isNew && (
              <span
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: colors.special.newBadgeDot }}
                aria-label="신규"
              />
            )}
            <span
              className="inline-flex items-center px-2 py-0.5"
              style={{
                background: colors.neutral.bg,
                color: colors.neutral.text,
                fontSize: typeScale.micro.fontSize,
                fontWeight: typeScale.micro.fontWeight,
                lineHeight: typeScale.micro.lineHeight,
                borderRadius: radius.chip,
                padding: '2px 6px',
              }}
            >
              {article.source}
            </span>
            <span style={{ color: colors.muted, fontSize: 12 }}>· {article.category}</span>
            {article.isNew && <span style={{ color: colors.muted, fontSize: 12 }}>· 속보</span>}
          </div>
          <span style={{ color: colors.muted, fontSize: 12 }}>{article.relativeTime}</span>
        </div>

        {/* Headline */}
        <p
          className="font-semibold overflow-hidden"
          style={{
            fontSize: typeScale.headline.fontSize,
            lineHeight: typeScale.headline.lineHeight,
            letterSpacing: typeScale.headline.letterSpacing,
            color: isRead ? colors.muted : colors.primary,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            marginBottom: isLoggedIn && article.tags.length > 0 ? spacing.sm : 0,
          }}
        >
          {article.headline}
        </p>

        {/* Tag chips — logged-in only */}
        {isLoggedIn && article.tags.length > 0 && (
          <div className="flex gap-1.5 mt-2">
            {article.tags.slice(0, 2).map((tag) => (
              <span
                key={tag}
                style={{
                  background: colors.accentTint,
                  color: colors.accent,
                  fontSize: typeScale.micro.fontSize,
                  fontWeight: typeScale.micro.fontWeight,
                  borderRadius: radius.chip,
                  padding: '2px 8px',
                  lineHeight: 1.5,
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </button>
    )
  },
)

// 세션(로그인 여부) 조회 중 보여주는 페이지 전체 스켈레톤. 게스트/로그인 전용 텍스트나
// 필터를 확정하지 않고, 중립적인 자리표시자만 그린다.
function NewsFeedPageSkeleton() {
  return (
    <div className="md:pl-0" style={{ paddingLeft: 0 }}>
      <div className="sticky z-30 bg-slate-50 border-b border-slate-200" style={{ top: 56 }}>
        <div className="mx-auto px-4 md:px-6" style={{ maxWidth: 760 + 64 }}>
          <div className="flex items-center gap-2 py-3 animate-pulse" style={{ paddingLeft: 64 }}>
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-8 w-16 rounded-md bg-slate-100 shrink-0" />
            ))}
          </div>
        </div>
      </div>
      <div className="mx-auto py-6 px-4" style={{ maxWidth: 760 + 64, paddingLeft: 80 }}>
        <div className="h-6 w-40 rounded bg-slate-100 animate-pulse mb-4" />
        <SkeletonFeed />
      </div>
    </div>
  )
}

function SkeletonFeed() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden animate-pulse">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="px-5 py-4"
          style={{ borderBottom: i < 2 ? `1px solid ${colors.border}` : 'none' }}
        >
          <div className="flex justify-between mb-3">
            <div className="flex gap-2">
              <div className="h-4 w-14 rounded bg-slate-100" />
              <div className="h-4 w-8 rounded bg-slate-100" />
            </div>
            <div className="h-4 w-12 rounded bg-slate-100" />
          </div>
          <div className="h-4 rounded bg-slate-100 mb-2" />
          <div className="h-4 rounded bg-slate-100 w-3/4" />
        </div>
      ))}
    </div>
  )
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-slate-700 text-[15px] font-medium mb-1">뉴스를 불러오지 못했습니다</p>
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

function EmptyState({
  isLoggedIn,
  navigate,
}: {
  isLoggedIn: boolean
  navigate: (p: string) => void
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {isLoggedIn ? (
        <>
          <p className="text-slate-700 text-[15px] font-medium mb-1">아직 관심 태그가 없어요</p>
          <p className="text-slate-500 text-[13px] mb-4">
            관심 있는 주제를 선택하면 맞춤 뉴스를 받아볼 수 있습니다
          </p>
          <button
            onClick={() => navigate('/settings')}
            className="h-10 px-4 rounded-lg text-[14px] font-medium"
            style={{ background: colors.accent, color: colors.surface, borderRadius: radius.control }}
          >
            태그 고르기
          </button>
        </>
      ) : (
        <>
          <p className="text-slate-700 text-[15px] font-medium mb-1">이 카테고리의 기사가 없습니다</p>
          <p className="text-slate-500 text-[13px]">다른 카테고리를 선택해보세요</p>
        </>
      )}
    </div>
  )
}
