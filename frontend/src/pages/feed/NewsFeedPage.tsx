import { useRef, useState, forwardRef, type RefObject } from 'react'
import { useNavigate, useParams, useSearchParams, useLocation } from 'react-router-dom'
import type { Article } from '../../types/feed'
import { useAuth } from '../../hooks/useAuth'
import { useFeed } from '../../hooks/useFeed'
import { useTags } from '../../hooks/useTags'
import { categoryNames } from '../../api/tags'
import { colors, typeScale, radius, spacing } from '../../constants/theme'
import ArticleModal from '../../components/feed/ArticleModal'

const ALL_FILTER = '전체'

// "/"와 "/articles/:id" 둘 다 이 컴포넌트로 연결된다(routes/AppRoutes.tsx). 목록과
// 모달을 같은 컴포넌트가 다루므로 openArticleId는 prop이 아니라 라우트 파라미터에서
// 직접 읽는다 — 열기/닫기는 navigate()로, 상세 URL은 useParams로 확인한다.
export default function NewsFeedPage() {
  const { id: paramArticleId } = useParams<{ id: string }>()
  const openArticleId = paramArticleId ?? null
  const { user, isLoggedIn, isLoading: isSessionLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const searchQuery = searchParams.get('q') ?? ''
  const [activeFilter, setActiveFilter] = useState(ALL_FILTER)
  const [readIds, setReadIds] = useState<Set<string>>(new Set())
  const [reachedEnd, setReachedEnd] = useState(false)
  const rowRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  // 게스트 필터 칩은 서버 태그 중 카테고리 성격인 것만 쓴다(design_plan §7 표).
  // 로그인 시에는 사용자 관심 태그를 쓴다.
  const { data: allTags = [] } = useTags()
  const userTags = user?.userTags ?? []
  const guestCategories = categoryNames(allTags)
  const filters = isLoggedIn ? [ALL_FILTER, ...userTags] : [ALL_FILTER, ...guestCategories]

  const {
    data: feedPage,
    isLoading: isFeedLoading,
    isError,
    refetch,
  } = useFeed({ activeFilter, query: searchQuery })
  const articles = feedPage?.articles ?? []

  // 필터나 검색어가 바뀌면 "끝 도달" 표시를 다시 접는다. 이펙트 대신 렌더 중 상태 조정
  // 패턴을 쓴다 (react-hooks/set-state-in-effect — 이펙트 안에서 setState하면 렌더가
  // 한 번 더 캐스케이드된다). 두 값을 한 키로 묶어 비교한다.
  const feedKey = `${activeFilter}\u0000${searchQuery}`
  const [prevFeedKey, setPrevFeedKey] = useState(feedKey)
  if (prevFeedKey !== feedKey) {
    setPrevFeedKey(feedKey)
    setReachedEnd(false)
  }

  // 목록에서 찾는다. 목록에 없는 기사(예: 뒤쪽 페이지의 기사 URL로 직접 진입)는
  // 아직 열 수 없다 — 단건 조회 API(GET /articles/{id})가 없다.
  const openArticle = articles.find((a) => a.id === openArticleId) ?? null

  // 모달을 열고 닫을 때 location.search를 그대로 넘긴다 — 빠뜨리면 기사를 열었다 닫는
  // 순간 `?q=`가 사라져 검색 결과가 초기화된다.
  const handleOpenArticle = (id: string) => {
    setReadIds((prev) => new Set([...prev, id]))
    navigate({ pathname: `/articles/${id}`, search: location.search })
  }

  const handleCloseArticle = () => {
    navigate({ pathname: '/', search: location.search })
    if (openArticleId) {
      setTimeout(() => rowRefs.current[openArticleId]?.focus(), 50)
    }
  }

  const clearSearch = () => navigate('/')

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

          {/* 검색 컨텍스트 — 무엇으로 걸러진 목록인지 보여주고 되돌릴 수단을 준다.
              헤더(56px) + 필터바 밖의 본문 흐름에 둔다: design_plan §4의
              "상단 고정 영역 최대 2단, 합계 120px 이하"를 넘기지 않기 위해 sticky로 만들지 않았다. */}
          {searchQuery && (
            <div
              className="flex items-center justify-between gap-3 mb-5"
              style={{
                padding: `${spacing.md}px ${spacing.lg}px`,
                background: colors.surface,
                border: `1px solid ${colors.border}`,
                borderRadius: radius.card,
              }}
            >
              <p className="min-w-0" style={{ fontSize: typeScale.caption.fontSize }}>
                <span style={{ color: colors.muted }}>검색</span>{' '}
                <span style={{ color: colors.primary, fontWeight: 500 }}>“{searchQuery}”</span>
                {!isFeedLoading && !isError && (
                  <span style={{ color: colors.muted }}> · {articles.length}건</span>
                )}
              </p>
              <button
                onClick={clearSearch}
                className="shrink-0"
                style={{
                  height: 32,
                  padding: `0 ${spacing.md}px`,
                  border: `1px solid ${colors.border}`,
                  borderRadius: radius.control,
                  background: colors.surface,
                  color: colors.neutral.text,
                  fontSize: typeScale.micro.fontSize,
                  fontWeight: 500,
                }}
              >
                검색 초기화
              </button>
            </div>
          )}

          {/* Guest login banner — 검색 중에는 감춘다(목적이 뚜렷한 화면에 배너를 겹치지 않는다)

              로그인 버튼은 두지 않는다. 헤더 우측에 비로그인 상태면 항상 로그인 버튼이
              떠 있어서(components/common/Header.tsx), 같은 화면에 같은 동작의 버튼이
              둘이 되면 어느 쪽을 눌러야 하는지 고민하게 만든다. 배너는 안내만 한다. */}
          {!isLoggedIn && !searchQuery && (
            <div className="px-4 py-3 rounded-xl border border-slate-200 bg-white mb-5">
              <p className="text-slate-700 text-[15px]">
                로그인하고 관심사에 맞는 뉴스를 받아보세요
              </p>
            </div>
          )}

          {/* Feed states */}
          {isFeedLoading && <SkeletonFeed />}

          {isError && <ErrorState onRetry={() => refetch()} />}

          {!isFeedLoading && !isError && articles.length === 0 && (
            <EmptyState
              isLoggedIn={isLoggedIn}
              navigate={navigate}
              searchQuery={searchQuery}
              onClearSearch={clearSearch}
            />
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
          allArticles={articles}
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
  searchQuery,
  onClearSearch,
}: {
  isLoggedIn: boolean
  navigate: (p: string) => void
  searchQuery: string
  onClearSearch: () => void
}) {
  // 검색 결과 없음은 "기사가 원래 없음"과 다른 상태다. design_plan §4가 요구하는 대로
  // 다음 행동(검색 초기화)을 함께 제시한다.
  if (searchQuery) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-slate-700 text-[15px] font-medium mb-1">
          “{searchQuery}”와 일치하는 기사가 없습니다
        </p>
        <p className="text-slate-500 text-[13px] mb-4">
          다른 검색어를 입력하거나 검색을 초기화해보세요
        </p>
        <button
          onClick={onClearSearch}
          className="h-10 px-4 rounded-lg text-[14px] font-medium"
          style={{ background: colors.accent, color: colors.surface, borderRadius: radius.control }}
        >
          검색 초기화
        </button>
      </div>
    )
  }

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
