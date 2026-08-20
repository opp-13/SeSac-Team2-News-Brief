import { useEffect } from 'react'
import type { RefObject } from 'react'

// frontend/CLAUDE.md §7 "포커스 트랩, ESC 닫기, 포커스 복귀는 선택이 아니라 필수"
// (모달·드로어 공통). containerRef 내부의 포커스 가능한 요소들 사이에서만 Tab이
// 순환하도록 해서, 열려있는 동안 Tab 이동이 모달 밖으로 나가지 않게 한다.
export function useFocusTrap(containerRef: RefObject<HTMLElement | null>, active: boolean) {
  useEffect(() => {
    if (!active) return

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Tab' || !containerRef.current) return
      const focusable = containerRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])',
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [containerRef, active])
}
