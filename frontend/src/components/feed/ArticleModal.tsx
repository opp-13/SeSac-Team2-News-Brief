import { useEffect, useRef, useState, useCallback, type RefObject } from 'react'
import type { Article } from '../../types/feed'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { colors, typeScale, radius } from '../../constants/theme'

// docs/figma-export/components/ArticleModal.tsx 이식.
//
// §2 표 적용: named export → default export, 하드코딩 색상 → theme.ts 토큰(정확히
// 일치하는 것만). 20px 헤드라인, 모바일 바텀시트 상단 모서리 16px은 theme.ts의 공용
// 스케일엔 없지만 design_plan.md §6.3이 이 모달 전용으로 명시한 값이라(§3의 일반
// 타입 스케일과 별개) 그대로 리터럴로 둔다 — 토큰 부재가 아니라 문서에 있는 값이다.
//
// props 구조(article/allArticles/onClose/onNavigate)는 그대로 유지한다 — NewsFeedPage가
// useParams로 openArticleId를 읽고 navigate()로 열고 닫는 라우팅 로직을 이미 담당하고
// 있어서, 이 컴포넌트는 원본처럼 콜백만 받으면 된다.
//
// loading/error 상태는 useState+setTimeout을 그대로 뒀다 — §2 규칙2가 겨냥한 "목업
// 데이터 fetch"가 아니라, article이 이미 props로 다 있는 상태에서 상세 화면 전환 시
// 잠깐 스켈레톤을 보여주는 UX 트랜지션이라 TanStack Query 대상이 아니라고 판단했다.
//
// 접근성: 원본은 "열릴 때 포커스 이동 + 닫히면 포커스 복귀"만 있었고 실제 Tab 트랩은
// 없었다(Tab이 모달 밖으로 나갈 수 있었음). frontend/CLAUDE.md §7이 포커스 트랩을
// "선택이 아니라 필수"로 못박아서, hooks/useFocusTrap.ts로 진짜 트랩을 추가했다 —
// "그대로 살려달라"는 요청과는 다르게, 원본에 없던 걸 CLAUDE.md 요구사항에 맞춰 채운
// 부분이니 알려드린다.

interface Props {
  article: Article | null
  allArticles: Article[]
  onClose: () => void
  onNavigate: (id: string) => void
}

type ModalState = 'loading' | 'error' | 'ready'

export default function ArticleModal({ article, allArticles, onClose, onNavigate }: Props) {
  const [state, setState] = useState<ModalState>('loading')
  const [seenArticleId, setSeenArticleId] = useState(article?.id)
  const modalRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const isDesktop = window.innerWidth >= 768

  const currentIndex = allArticles.findIndex((a) => a.id === article?.id)
  const hasPrev = currentIndex > 0
  const hasNext = currentIndex < allArticles.length - 1

  useFocusTrap(modalRef, !!article)

  // 기사가 바뀌면(최초 열림 포함) 로딩 상태로 되돌린다. 이펙트 안에서 setState를 바로
  // 부르는 대신 렌더 중 상태 조정 패턴을 쓴다 — react-hooks/set-state-in-effect가
  // 걸리는 걸 피하기 위함(NewsFeedPage의 prevActiveFilter와 같은 이유).
  if (article?.id !== seenArticleId) {
    setSeenArticleId(article?.id)
    setState('loading')
  }

  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement
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

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft' && hasPrev) onNavigate(allArticles[currentIndex - 1].id)
      if (e.key === 'ArrowRight' && hasNext) onNavigate(allArticles[currentIndex + 1].id)
    },
    [onClose, hasPrev, hasNext, currentIndex, allArticles, onNavigate],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  if (!article) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center md:items-center">
      {/* Overlay: design_plan.md §6.3 — #0F172A(colors.primary) 50% 투명도 */}
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
          modalRef={modalRef}
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
          modalRef={modalRef}
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
  closeButtonRef: RefObject<HTMLButtonElement | null>
  modalRef: RefObject<HTMLDivElement | null>
}

function DesktopModal({
  article,
  state,
  onClose,
  onRetry,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  closeButtonRef,
  modalRef,
}: ModalContentProps) {
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
        ref={modalRef}
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

function MobileBottomSheet({
  article,
  state,
  onClose,
  onRetry,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  closeButtonRef,
  modalRef,
}: ModalContentProps) {
  return (
    <div
      ref={modalRef}
      className="absolute bottom-0 left-0 right-0 bg-white z-10"
      // design_plan.md §6.3 모바일 스펙 — 상단 모서리만 16px (theme.ts 공용 스케일엔 없는,
      // 이 바텀시트 전용 값)
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

function ModalContent({
  article,
  state,
  onRetry,
}: {
  article: Article
  state: ModalState
  onRetry: () => void
}) {
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
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-700"
          style={{ fontSize: typeScale.micro.fontSize, borderRadius: radius.chip }}
        >
          {article.source}
        </span>
        <span className="text-slate-500" style={{ fontSize: typeScale.caption.fontSize }}>
          · {article.relativeTime}
        </span>
      </div>

      {/* Headline — design_plan.md §6.3 모달 전용 값(20px/600), 공용 타입 스케일엔 없음 */}
      <h2
        className="text-slate-900 font-semibold leading-snug mb-5"
        style={{ fontSize: 20, letterSpacing: '-0.01em', lineHeight: 1.4 }}
      >
        {article.headline}
      </h2>

      {/* AI Summary block */}
      <div className="mb-6">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-md mb-3"
          style={{
            background: colors.accentTint,
            color: colors.accent,
            fontSize: typeScale.micro.fontSize,
            fontWeight: typeScale.micro.fontWeight,
            borderRadius: radius.chip,
          }}
        >
          AI 요약
        </span>
        <div
          className="flex"
          style={{
            borderLeft: `2px solid ${colors.accent}`,
            borderRadius: `0 ${radius.chip}px ${radius.chip}px 0`,
          }}
        >
          <p
            className="pl-3 text-slate-700"
            style={{
              fontSize: typeScale.body.fontSize,
              lineHeight: typeScale.body.lineHeight,
              fontWeight: typeScale.body.fontWeight,
            }}
          >
            {article.summary}
          </p>
        </div>
      </div>

      {/* Translation placeholder — frontend/CLAUDE.md §0.2: 담당자 부재로 화면 없이 자리만 */}
      <div className="h-8" aria-hidden="true" />

      {/* Actions */}
      <div className="flex items-center gap-3">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 h-10 px-4 rounded-lg text-white text-[14px] font-medium"
          style={{ background: colors.accent }}
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
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function ChevronLeft() {
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
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function ChevronRight() {
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
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

function ExternalLinkIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  )
}
