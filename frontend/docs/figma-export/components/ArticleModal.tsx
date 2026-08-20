import { useEffect, useRef, useState, useCallback } from 'react'
import type { Article } from '../types'

interface Props {
  article: Article | null
  allArticles: Article[]
  onClose: () => void
  onNavigate: (id: string) => void
}

type ModalState = 'loading' | 'error' | 'ready'

export function ArticleModal({ article, allArticles, onClose, onNavigate }: Props) {
  const [state, setState] = useState<ModalState>('loading')
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const isDesktop = window.innerWidth >= 768

  const currentIndex = allArticles.findIndex((a) => a.id === article?.id)
  const hasPrev = currentIndex > 0
  const hasNext = currentIndex < allArticles.length - 1

  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement
    setState('loading')
    const timer = setTimeout(() => setState('ready'), 600)
    return () => clearTimeout(timer)
  }, [article?.id])

  useEffect(() => {
    if (state === 'ready') {
      closeButtonRef.current?.focus()
    }
  }, [state])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
      previousFocusRef.current?.focus()
    }
  }, [])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
    if (e.key === 'ArrowLeft' && hasPrev) onNavigate(allArticles[currentIndex - 1].id)
    if (e.key === 'ArrowRight' && hasNext) onNavigate(allArticles[currentIndex + 1].id)
  }, [onClose, hasPrev, hasNext, currentIndex, allArticles, onNavigate])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  if (!article) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center md:items-center">
      {/* Overlay */}
      <div
        className="absolute inset-0"
        style={{ background: 'rgba(15, 23, 42, 0.5)' }}
        onClick={onClose}
        aria-hidden="true"
      />

      {isDesktop ? (
        <DesktopModal
          article={article}
          state={state}
          onClose={onClose}
          onRetry={() => setState('loading')}
          hasPrev={hasPrev}
          hasNext={hasNext}
          onPrev={() => hasPrev && onNavigate(allArticles[currentIndex - 1].id)}
          onNext={() => hasNext && onNavigate(allArticles[currentIndex + 1].id)}
          closeButtonRef={closeButtonRef}
        />
      ) : (
        <MobileBottomSheet
          article={article}
          state={state}
          onClose={onClose}
          onRetry={() => setState('loading')}
          hasPrev={hasPrev}
          hasNext={hasNext}
          onPrev={() => hasPrev && onNavigate(allArticles[currentIndex - 1].id)}
          onNext={() => hasNext && onNavigate(allArticles[currentIndex + 1].id)}
          closeButtonRef={closeButtonRef}
        />
      )}
    </div>
  )
}

interface ModalContentProps {
  article: Article
  state: ModalState
  onClose: () => void
  onRetry: () => void
  hasPrev: boolean
  hasNext: boolean
  onPrev: () => void
  onNext: () => void
  closeButtonRef: React.RefObject<HTMLButtonElement | null>
}

function DesktopModal({ article, state, onClose, onRetry, hasPrev, hasNext, onPrev, onNext, closeButtonRef }: ModalContentProps) {
  return (
    <div className="relative z-10 flex items-center gap-4 px-4" style={{ width: '100%', maxWidth: 760 }}>
      {/* Prev button */}
      <button
        onClick={onPrev}
        disabled={!hasPrev}
        className="w-10 h-10 flex items-center justify-center rounded-full bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
        aria-label="이전 기사"
      >
        <ChevronLeft />
      </button>

      <div
        className="flex-1 bg-white rounded-xl overflow-hidden"
        style={{ maxHeight: '80vh' }}
        role="dialog"
        aria-modal="true"
        aria-label={article.headline}
      >
        <div className="overflow-y-auto" style={{ maxHeight: '80vh', padding: 32 }}>
          {/* Close button */}
          <div className="flex justify-end mb-4">
            <button
              ref={closeButtonRef}
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              aria-label="닫기"
            >
              <CloseIcon />
            </button>
          </div>

          <ModalContent article={article} state={state} onRetry={onRetry} />
        </div>
      </div>

      {/* Next button */}
      <button
        onClick={onNext}
        disabled={!hasNext}
        className="w-10 h-10 flex items-center justify-center rounded-full bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
        aria-label="다음 기사"
      >
        <ChevronRight />
      </button>
    </div>
  )
}

function MobileBottomSheet({ article, state, onClose, onRetry, hasPrev, hasNext, onPrev, onNext, closeButtonRef }: ModalContentProps) {
  return (
    <div
      className="absolute bottom-0 left-0 right-0 bg-white z-10"
      style={{ borderRadius: '16px 16px 0 0', maxHeight: '90vh' }}
      role="dialog"
      aria-modal="true"
      aria-label={article.headline}
    >
      {/* Drag handle */}
      <div className="flex justify-center pt-3 pb-1">
        <div className="w-9 h-1 rounded-full bg-slate-300" />
      </div>

      <div className="overflow-y-auto" style={{ maxHeight: 'calc(90vh - 40px)', padding: '0 20px 20px' }}>
        <div className="flex justify-end py-2">
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-slate-400"
            aria-label="닫기"
          >
            <CloseIcon />
          </button>
        </div>

        <ModalContent article={article} state={state} onRetry={onRetry} />

        {/* Mobile prev/next */}
        <div className="flex gap-2 mt-6">
          <button
            onClick={onPrev}
            disabled={!hasPrev}
            className="flex-1 h-10 flex items-center justify-center gap-1 border border-slate-200 rounded-lg text-slate-700 text-sm disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft /> 이전
          </button>
          <button
            onClick={onNext}
            disabled={!hasNext}
            className="flex-1 h-10 flex items-center justify-center gap-1 border border-slate-200 rounded-lg text-slate-700 text-sm disabled:opacity-30 disabled:cursor-not-allowed"
          >
            다음 <ChevronRight />
          </button>
        </div>
      </div>
    </div>
  )
}

function ModalContent({ article, state, onRetry }: { article: Article; state: ModalState; onRetry: () => void }) {
  if (state === 'loading') {
    return (
      <div className="animate-pulse">
        <div className="flex gap-2 mb-4">
          <div className="h-5 w-16 rounded bg-slate-100" />
          <div className="h-5 w-12 rounded bg-slate-100" />
        </div>
        <div className="h-6 rounded bg-slate-100 mb-2" />
        <div className="h-6 rounded bg-slate-100 mb-2 w-4/5" />
        <div className="mt-6 space-y-2">
          <div className="h-4 rounded bg-slate-100" />
          <div className="h-4 rounded bg-slate-100" />
          <div className="h-4 rounded bg-slate-100 w-3/4" />
        </div>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-slate-700 text-[15px] font-medium mb-1">기사를 불러오지 못했습니다</p>
        <p className="text-slate-500 text-[13px] mb-4">잠시 후 다시 시도해주세요</p>
        <button
          onClick={onRetry}
          className="h-8 px-4 rounded-lg border border-slate-200 text-slate-700 text-[13px] hover:bg-slate-50"
        >
          다시 시도
        </button>
      </div>
    )
  }

  return (
    <>
      {/* Meta */}
      <div className="flex items-center gap-2 mb-3">
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700" style={{ fontSize: 12, borderRadius: 6 }}>
          {article.source}
        </span>
        <span className="text-slate-500" style={{ fontSize: 13 }}>· {article.relativeTime}</span>
      </div>

      {/* Headline */}
      <h2 className="text-slate-900 font-semibold leading-snug mb-5" style={{ fontSize: 20, letterSpacing: '-0.01em', lineHeight: 1.4 }}>
        {article.headline}
      </h2>

      {/* AI Summary block */}
      <div className="mb-6">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-md mb-3"
          style={{ background: '#CFFAFE', color: '#155E75', fontSize: 12, fontWeight: 500, borderRadius: 6 }}
        >
          AI 요약
        </span>
        <div
          className="flex"
          style={{ borderLeft: '2px solid #155E75', borderRadius: '0 6px 6px 0' }}
        >
          <p
            className="pl-3 text-slate-700"
            style={{ fontSize: 15, lineHeight: 1.6, fontWeight: 400 }}
          >
            {article.summary}
          </p>
        </div>
      </div>

      {/* Translation placeholder */}
      <div className="h-8" aria-hidden="true" />

      {/* Actions */}
      <div className="flex items-center gap-3">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 h-10 px-4 rounded-lg text-white text-[14px] font-medium"
          style={{ background: '#155E75' }}
        >
          원문 보기
          <ExternalLinkIcon />
        </a>
      </div>
    </>
  )
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function ChevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function ChevronRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

function ExternalLinkIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  )
}
