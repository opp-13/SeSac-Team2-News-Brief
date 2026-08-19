import { useState, useRef, useEffect } from 'react'
import type { Article } from '../types'
import { mockArticles } from '../data/mockData'
import { ArticleModal } from '../components/ArticleModal'

interface Props {
  isLoggedIn: boolean
  userTags: string[]
  openArticleId: string | null
  onOpenArticle: (id: string) => void
  onCloseArticle: () => void
  navigate: (path: string) => void
}

const GUEST_CATEGORIES = ['전체', 'IT', '경제', '정치', '글로벌', '스타트업', '보안']

type FeedState = 'loading' | 'empty' | 'error' | 'ready' | 'end'

export function NewsFeedPage({ isLoggedIn, userTags, openArticleId, onOpenArticle, onCloseArticle, navigate }: Props) {
  const [activeFilter, setActiveFilter] = useState('전체')
  const [feedState, setFeedState] = useState<FeedState>('loading')
  const [articles, setArticles] = useState<Article[]>([])
  const [readIds, setReadIds] = useState<Set<string>>(new Set())
  const rowRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  const filters = isLoggedIn ? ['전체', ...userTags] : GUEST_CATEGORIES

  useEffect(() => {
    setFeedState('loading')
    const timer = setTimeout(() => {
      const filtered = activeFilter === '전체'
        ? mockArticles
        : mockArticles.filter((a) =>
            isLoggedIn
              ? a.tags.includes(activeFilter)
              : a.category === activeFilter
          )
      setArticles(filtered)
      setFeedState(filtered.length === 0 ? 'empty' : 'ready')
    }, 700)
    return () => clearTimeout(timer)
  }, [activeFilter, isLoggedIn])

  const openArticle = mockArticles.find((a) => a.id === openArticleId) ?? null

  const handleOpenArticle = (id: string) => {
    setReadIds((prev) => new Set([...prev, id]))
    onOpenArticle(id)
  }

  const handleCloseArticle = () => {
    onCloseArticle()
    if (openArticleId) {
      setTimeout(() => rowRefs.current[openArticleId]?.focus(), 50)
    }
  }

  return (
    <>
      <div className="md:pl-0" style={{ paddingLeft: 0 }}>
        {/* Sticky filter bar */}
        <div
          className="sticky z-30 bg-slate-50 border-b border-slate-200"
          style={{ top: 56 }}
        >
          <div className="mx-auto px-4 md:px-6" style={{ maxWidth: 760 + 64 }}>
            <div className="flex items-center gap-2 py-3 overflow-x-auto no-scrollbar" style={{ paddingLeft: 64 }}>
              {filters.map((filter) => (
                <button
                  key={filter}
                  onClick={() => setActiveFilter(filter)}
                  className="shrink-0 h-8 px-3 rounded-md text-sm transition-colors"
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    borderRadius: 6,
                    background: activeFilter === filter ? '#0F172A' : '#FFFFFF',
                    color: activeFilter === filter ? '#FFFFFF' : '#334155',
                    border: activeFilter === filter ? 'none' : '1px solid #E2E8F0',
                  }}
                >
                  {filter}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Content */}
        <div
          className="mx-auto py-6 px-4"
          style={{ maxWidth: 760 + 64, paddingLeft: 80 }}
        >
          {/* Page heading */}
          <h1
            className="text-slate-900 font-semibold mb-4"
            style={{ fontSize: 22, letterSpacing: '-0.01em' }}
          >
            {isLoggedIn ? '관심사 기반 뉴스' : '최신 뉴스'}
          </h1>

          {/* Guest login banner */}
          {!isLoggedIn && (
            <div
              className="flex items-center justify-between px-4 py-3 rounded-xl border border-slate-200 bg-white mb-5"
            >
              <p className="text-slate-700 text-[14px]">
                로그인하고 관심사에 맞는 뉴스를 받아보세요
              </p>
              <button
                onClick={() => navigate('/login')}
                className="h-8 px-3 rounded-lg text-white text-[13px] font-medium shrink-0"
                style={{ background: '#155E75', borderRadius: 8 }}
              >
                로그인
              </button>
            </div>
          )}

          {/* Feed states */}
          {feedState === 'loading' && <SkeletonFeed />}

          {feedState === 'error' && (
            <ErrorState onRetry={() => setFeedState('loading')} />
          )}

          {feedState === 'empty' && (
            <EmptyState isLoggedIn={isLoggedIn} navigate={navigate} />
          )}

          {(feedState === 'ready' || feedState === 'end') && (
            <>
              <ArticleList
                articles={articles}
                isLoggedIn={isLoggedIn}
                readIds={readIds}
                openArticleId={openArticleId}
                onOpen={handleOpenArticle}
                rowRefs={rowRefs}
              />
              {feedState === 'end' && (
                <p className="text-center text-slate-400 text-[13px] py-8">
                  더 이상 기사가 없습니다
                </p>
              )}
              {feedState === 'ready' && (
                <button
                  onClick={() => setFeedState('end')}
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
  rowRefs: React.MutableRefObject<Record<string, HTMLButtonElement | null>>
}) {
  return (
    <div
      className="bg-white rounded-xl border border-slate-200"
      style={{ borderRadius: 12 }}
    >
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
            ref={(el) => { rowRefs.current[article.id] = el }}
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

import { forwardRef } from 'react'

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
          background: isActive ? '#F8FAFC' : 'transparent',
          borderBottom: isLast ? 'none' : '1px solid #E2E8F0',
          padding: '14px 20px',
        }}
        onMouseEnter={(e) => {
          if (!isActive) (e.currentTarget as HTMLElement).style.background = '#F8FAFC'
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
                style={{ background: '#F59E0B' }}
                aria-label="신규"
              />
            )}
            <span
              className="inline-flex items-center px-2 py-0.5"
              style={{
                background: '#F1F5F9',
                color: '#334155',
                fontSize: 12,
                fontWeight: 500,
                borderRadius: 6,
                lineHeight: 1,
                padding: '2px 6px',
              }}
            >
              {article.source}
            </span>
            <span style={{ color: '#64748B', fontSize: 12 }}>· {article.category}</span>
            {article.isNew && (
              <span style={{ color: '#64748B', fontSize: 12 }}>· 속보</span>
            )}
          </div>
          <span style={{ color: '#64748B', fontSize: 12 }}>{article.relativeTime}</span>
        </div>

        {/* Headline */}
        <p
          className="font-semibold overflow-hidden"
          style={{
            fontSize: 16,
            lineHeight: 1.4,
            letterSpacing: '-0.01em',
            color: isRead ? '#64748B' : '#0F172A',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            marginBottom: isLoggedIn && article.tags.length > 0 ? 8 : 0,
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
                  background: '#CFFAFE',
                  color: '#155E75',
                  fontSize: 12,
                  fontWeight: 500,
                  borderRadius: 6,
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
  }
)

function SkeletonFeed() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden animate-pulse">
      {[0, 1, 2].map((i) => (
        <div key={i} className="px-5 py-4" style={{ borderBottom: i < 2 ? '1px solid #E2E8F0' : 'none' }}>
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
        style={{ background: '#155E75', color: '#fff', borderRadius: 8 }}
      >
        다시 시도
      </button>
    </div>
  )
}

function EmptyState({ isLoggedIn, navigate }: { isLoggedIn: boolean; navigate: (p: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {isLoggedIn ? (
        <>
          <p className="text-slate-700 text-[15px] font-medium mb-1">아직 관심 태그가 없어요</p>
          <p className="text-slate-500 text-[13px] mb-4">관심 있는 주제를 선택하면 맞춤 뉴스를 받아볼 수 있습니다</p>
          <button
            onClick={() => navigate('/settings')}
            className="h-10 px-4 rounded-lg text-[14px] font-medium"
            style={{ background: '#155E75', color: '#fff', borderRadius: 8 }}
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
