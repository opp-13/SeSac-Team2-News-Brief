import { http, HttpResponse } from 'msw'
import { mockArticles } from './feedMockData'

const BASE = '/api/v1'

// 브라우저 세션 동안만 유지되는 목업 로그인 상태. 새로고침하면 초기화된다 —
// 실제 서버 세션(Redis)을 흉내내는 최소 구현이며 영속화하지 않는다.
let mockSession: { isAdmin: boolean; userTags: string[] } | null = null

export const handlers = [
  // docs/api-contracts/auth.md — 세션 없으면 401(비로그인), 있으면 200.
  http.get(`${BASE}/auth/me`, () => {
    if (!mockSession) {
      return HttpResponse.json(
        { success: false, error: { code: 'UNAUTHENTICATED', message: '로그인이 필요합니다.' } },
        { status: 401 },
      )
    }
    return HttpResponse.json({
      success: true,
      data: { isLoggedIn: true, isAdmin: mockSession.isAdmin, userTags: mockSession.userTags },
    })
  }),

  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email?: string; password?: string }
    if (!body.email || !body.password) {
      return HttpResponse.json(
        {
          success: false,
          error: { code: 'INVALID_CREDENTIALS', message: '이메일과 비밀번호를 입력해주세요.' },
        },
        { status: 400 },
      )
    }
    mockSession = { isAdmin: body.email.includes('admin'), userTags: ['AI', '개발'] }
    return HttpResponse.json({
      success: true,
      data: { isLoggedIn: true, isAdmin: mockSession.isAdmin, userTags: mockSession.userTags },
    })
  }),

  http.post(`${BASE}/auth/logout`, () => {
    mockSession = null
    return HttpResponse.json({ success: true, data: null })
  }),

  // SignupPage — docs/api-contracts/auth.md에 아직 없는 임시 경로(api/auth.ts 참고).
  // 로그인과 달리 이메일에 "admin"이 들어가도 관리자로 만들지 않는다 — 관리자 계정은
  // 가입이 아니라 로그인 목업 전용 이스터에그였다(원본 App.tsx도 그랬음).
  http.post(`${BASE}/auth/signup`, async ({ request }) => {
    const body = (await request.json()) as { email?: string; password?: string; userTags?: string[] }
    if (!body.email || !body.password) {
      return HttpResponse.json(
        {
          success: false,
          error: { code: 'INVALID_CREDENTIALS', message: '이메일과 비밀번호를 입력해주세요.' },
        },
        { status: 400 },
      )
    }
    mockSession = { isAdmin: false, userTags: body.userTags ?? [] }
    return HttpResponse.json({
      success: true,
      data: { isLoggedIn: true, isAdmin: mockSession.isAdmin, userTags: mockSession.userTags },
    })
  }),

  // SettingsPage 저장 — docs/api-contracts/auth.md에 아직 없는 임시 경로(api/auth.ts
  // 참고). mockSession.userTags를 실제로 갱신해서, 저장 후 다른 화면(피드 등)이
  // /auth/me를 다시 불러도 값이 계속 맞게 해둔다.
  http.patch(`${BASE}/auth/me/tags`, async ({ request }) => {
    if (!mockSession) {
      return HttpResponse.json(
        { success: false, error: { code: 'UNAUTHENTICATED', message: '로그인이 필요합니다.' } },
        { status: 401 },
      )
    }
    const body = (await request.json()) as { tags?: string[] }
    mockSession.userTags = body.tags ?? []
    return HttpResponse.json({ success: true, data: mockSession.userTags })
  }),

  // TODO: docs/api-contracts/feed.md가 아직 없어 응답 형태가 임시다. hooks/useFeed.ts는
  // 아직 이 핸들러를 호출하지 않고 mocks/feedMockData.ts를 직접 감싸는 중 — api/feed.ts가
  // 생기면 이 핸들러로 교체 연결한다. 커서 페이지네이션 규약(§6)만 형태로 맞춰뒀다.
  http.get(`${BASE}/feed`, () => {
    return HttpResponse.json({
      success: true,
      data: { articles: mockArticles, nextCursor: null, hasNext: false },
    })
  }),

  // docs/api-contracts/meta.md (DRAFT, 백엔드 미구현) — CI/CD 배포 검증용 목업.
  // 브라우저는 실제 XFF 헤더를 넣지 않으므로(그건 리버스 프록시가 하는 일) 샘플 값을 고정으로 준다.
  http.get(`${BASE}/meta/deploy-info`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        apiVersion: '0.1.0-mock',
        serverIp: '127.0.0.1',
        serverName: 'local-msw-mock',
        clientIp: '203.0.113.10',
        xForwardedFor: '203.0.113.10, 10.0.0.5',
      },
    })
  }),
]
