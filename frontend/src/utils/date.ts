// 루트 CLAUDE.md §7: "시각은 ISO 8601 UTC로 받고, KST 변환은 utils/date.ts에서 처리".
// docs/api-contracts/feed.md도 relativeTime을 서버가 만들지 않는다고 명시한다 —
// 서버는 publishedAt만 주고 "12분 전" 같은 표현은 여기서 만든다. 서버가 만들면
// 응답을 캐시한 순간 시간이 굳어버린다.

/** 백엔드가 타임존 표기 없이 UTC 시각을 보내는 경우가 있어(`2026-08-20T01:47:03`) Z를 붙여 해석한다. */
function parseUtc(iso: string): Date {
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(iso)
  return new Date(hasZone ? iso : `${iso}Z`)
}

/**
 * 발행 시각을 목록에 쓰는 짧은 표현으로 바꾼다.
 * 1분 미만 "방금", 1시간 미만 "N분 전", 24시간 미만 "N시간 전",
 * 어제는 "어제", 그 이상은 "M월 D일".
 */
export function toRelativeTime(iso: string, now: Date = new Date()): string {
  const then = parseUtc(iso)
  if (Number.isNaN(then.getTime())) return ''

  const diffMs = now.getTime() - then.getTime()
  // 서버 시계가 조금 앞서 있어도 "-3분 전"처럼 보이지 않게 한다.
  if (diffMs < 60_000) return '방금'

  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 60) return `${minutes}분 전`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`

  const days = Math.floor(hours / 24)
  if (days === 1) return '어제'

  // KST 기준 날짜로 표시한다 (사용자가 한국에 있다고 가정하지 않고 브라우저 로컬을 쓴다).
  return `${then.getMonth() + 1}월 ${then.getDate()}일`
}
