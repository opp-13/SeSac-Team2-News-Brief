import { http, HttpResponse } from 'msw'
import { mockArticles } from './feedMockData'

const BASE = '/api/v1'

// 오프라인/테스트용 목업. 기본은 꺼져 있고 VITE_USE_MSW=true 일 때만 뜬다(main.tsx).
//
// **응답 형태를 실제 백엔드와 같게 유지하는 것이 이 파일의 유일한 규칙이다.**
// api 레이어(api/auth.ts, api/feed.ts)가 백엔드 필드명을 기준으로 매핑하므로,
// 여기서 프런트 타입을 그대로 흘려보내면 목업 모드에서만 화면이 깨진다.
// 기준: backend/app/modules/{auth,feed}/schemas/*.py

interface MockUser {
  id: number
  email: string
  nickname: string
  role: 'USER' | 'ADMIN'
  preferredLanguage: string
  createdAt: string
}

const ALL_TAGS = [
  { id: 1, name: 'IT', tagType: 'CATEGORY' },
  { id: 2, name: '경제', tagType: 'CATEGORY' },
  { id: 3, name: '정치', tagType: 'CATEGORY' },
  { id: 4, name: '글로벌', tagType: 'CATEGORY' },
  { id: 5, name: '스타트업', tagType: 'CATEGORY' },
  { id: 6, name: '보안', tagType: 'CATEGORY' },
  { id: 7, name: 'AI', tagType: 'KEYWORD' },
  { id: 8, name: '개발', tagType: 'KEYWORD' },
  { id: 9, name: '반도체', tagType: 'KEYWORD' },
  { id: 10, name: '규제', tagType: 'KEYWORD' },
  { id: 11, name: '모바일', tagType: 'KEYWORD' },
]

// 브라우저 세션 동안만 유지되는 목업 로그인 상태. 새로고침하면 초기화된다 —
// 실제 서버 세션(Redis)을 흉내내는 최소 구현이며 영속화하지 않는다.
let mockUser: MockUser | null = null
let mockUserTagIds: number[] = []

const unauthorized = () =>
  HttpResponse.json(
    { success: false, error: { code: 'NO_SESSION', message: '로그인이 필요합니다.' } },
    { status: 401 },
  )

const ok = (data: unknown) => HttpResponse.json({ success: true, data })

function makeUser(email: string, nickname: string): MockUser {
  return {
    id: 1,
    email,
    nickname,
    // 실제 백엔드는 users.role을 읽는다. 목업에서는 관리자 화면을 확인할 수 있어야 하므로
    // 이메일에 "admin"이 들어가면 ADMIN으로 준다 — 목업 전용 편의이며 서버 동작이 아니다.
    role: email.includes('admin') ? 'ADMIN' : 'USER',
    preferredLanguage: 'ko',
    createdAt: new Date().toISOString(),
  }
}

/** mocks/feedMockData.ts(프런트 타입)를 백엔드 FeedItemResponse 형태로 되돌린다. */
function toBackendItem(article: (typeof mockArticles)[number], index: number) {
  return {
    feedItemId: mockUser ? index + 1 : null,
    articleId: Number(article.id),
    title: article.headline,
    press: article.source,
    publishedAt: article.publishedAt,
    language: 'ko',
    summary: article.summary,
    summaryType: 'THREE_LINE',
    originalUrl: article.url,
    tags: mockUser ? article.tags : [],
    category: article.category,
  }
}

export const handlers = [
  // ── auth ────────────────────────────────────────────────────────────────
  http.get(`${BASE}/auth/me`, () => (mockUser ? ok(mockUser) : unauthorized())),

  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email?: string; password?: string }
    if (!body.email || !body.password) {
      return HttpResponse.json(
        {
          success: false,
          error: { code: 'INVALID_CREDENTIALS', message: '이메일과 비밀번호를 입력해주세요.' },
        },
        { status: 401 },
      )
    }
    mockUser = makeUser(body.email, '목업사용자')
    mockUserTagIds = [7, 8] // AI, 개발
    return ok({ user: mockUser, sessionId: 'mock-session' })
  }),

  http.post(`${BASE}/auth/logout`, () => {
    mockUser = null
    mockUserTagIds = []
    return ok(null)
  }),

  // 실제 백엔드처럼 **세션을 만들지 않는다.** 사용자만 만들고 쿠키를 주지 않으므로
  // api/auth.ts의 signup()이 이어서 login()을 호출하는 흐름이 목업에서도 같게 재현된다.
  http.post(`${BASE}/auth/signup`, async ({ request }) => {
    const body = (await request.json()) as { email?: string; nickname?: string }
    if (!body.email) {
      return HttpResponse.json(
        {
          success: false,
          error: { code: 'VALIDATION_ERROR', message: '입력값이 올바르지 않습니다: email' },
        },
        { status: 422 },
      )
    }
    return ok(makeUser(body.email, body.nickname ?? '목업사용자'))
  }),

  // ── tags ────────────────────────────────────────────────────────────────
  http.get(`${BASE}/tags`, () => ok(ALL_TAGS)),

  http.get(`${BASE}/me/tags`, () =>
    mockUser ? ok(ALL_TAGS.filter((t) => mockUserTagIds.includes(t.id))) : unauthorized(),
  ),

  http.put(`${BASE}/me/tags`, async ({ request }) => {
    if (!mockUser) return unauthorized()
    const body = (await request.json()) as { tagIds?: number[] }
    mockUserTagIds = body.tagIds ?? []
    return ok(ALL_TAGS.filter((t) => mockUserTagIds.includes(t.id)))
  }),

  // ── feed ────────────────────────────────────────────────────────────────
  // 실제 백엔드처럼 게스트도 200을 받는다(게스트는 tags 빈 배열, feedItemId null).
  http.get(`${BASE}/feed`, ({ request }) => {
    const url = new URL(request.url)
    const tag = url.searchParams.get('tag')
    const q = url.searchParams.get('q')?.trim().toLowerCase()

    let items = mockArticles.map(toBackendItem)
    if (tag) {
      items = items.filter((i) => i.category === tag || i.tags.includes(tag))
    }
    if (q) {
      // 백엔드와 같은 범위(제목·언론사·요약·태그)로 맞춘다 — 좁으면 목업 모드에서만
      // "검색이 안 되는" 것처럼 보인다.
      items = items.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          (i.press ?? '').toLowerCase().includes(q) ||
          (i.summary ?? '').toLowerCase().includes(q) ||
          i.tags.some((t) => t.toLowerCase().includes(q)),
      )
    }
    return ok({ items, nextCursor: null, hasNext: false })
  }),

  // ── meta ────────────────────────────────────────────────────────────────
  // 브라우저는 실제 XFF 헤더를 넣지 않으므로(그건 리버스 프록시가 하는 일) 샘플 값을 준다.
  http.get(`${BASE}/meta/deploy-info`, () =>
    ok({
      apiVersion: '0.1.0-mock',
      serverIp: '127.0.0.1',
      serverName: 'local-msw-mock',
      clientIp: '203.0.113.10',
      xForwardedFor: '203.0.113.10, 10.0.0.5',
    }),
  ),
]
