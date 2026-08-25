// MSW 목업용 기사 데이터. `VITE_USE_MSW=true`일 때만 쓰인다 (main.tsx).
//
// handlers.ts가 이 모듈을 import하는데 파일이 리포에 없어서 `npm run build`가
// 깨져 있었다(프론트 배포 자체가 불가능한 상태였다). 필드는 handlers.ts의
// toBackendItem()이 읽는 것만 맞춘다 -- 백엔드 FeedItemResponse로 되돌리는 함수다.
//
// 실제 화면 확인은 백엔드를 띄워서 한다. 이 데이터는 백엔드 없이 프런트만 만질 때,
// 또는 오프라인일 때를 위한 것이다.

export interface MockArticle {
  id: string
  headline: string
  source: string
  publishedAt: string
  summary: string
  url: string
  tags: string[]
  category: string
}

// 발행 시각은 최신순 정렬을 확인할 수 있게 서로 다르게 둔다.
export const mockArticles: MockArticle[] = [
  {
    id: '1',
    headline: 'AI 반도체 시장, 내년까지 두 배 성장 전망',
    source: '연합뉴스',
    publishedAt: '2026-08-21T02:10:00Z',
    summary:
      '주요 조사기관이 AI 반도체 시장이 내년까지 두 배 규모로 커질 것으로 내다봤다. '
      + '데이터센터 수요가 성장을 이끌고, 전력 효율이 경쟁의 축으로 옮겨가고 있다.',
    url: 'https://example.com/news/1',
    tags: ['기술', '경제'],
    category: '기술',
  },
  {
    id: '2',
    headline: '중앙은행, 기준금리 동결 결정',
    source: '노컷뉴스',
    publishedAt: '2026-08-21T01:30:00Z',
    summary:
      '중앙은행이 기준금리를 현 수준으로 유지했다. 물가 둔화 흐름은 확인됐지만 '
      + '아직 추세로 보기 어렵다는 판단이다.',
    url: 'https://example.com/news/2',
    tags: ['경제', '금융'],
    category: '경제',
  },
  {
    id: '3',
    headline: '달 남극 얼음 탐사, 다음 단계로',
    source: 'Space Daily',
    publishedAt: '2026-08-20T23:05:00Z',
    summary:
      '달 남극의 영구 음영 지역에서 얼음을 찾는 탐사가 다음 단계로 넘어갔다. '
      + '현지 자원 활용이 장기 유인 탐사의 전제로 꼽힌다.',
    url: 'https://example.com/news/3',
    tags: ['과학'],
    category: '과학',
  },
  {
    id: '4',
    headline: '보안 취약점 공개, 즉시 업데이트 권고',
    source: 'digitimes',
    publishedAt: '2026-08-20T21:40:00Z',
    summary:
      '널리 쓰이는 플러그인에서 인증 없이 파일을 올릴 수 있는 취약점이 공개됐다. '
      + '개발사는 즉시 업데이트를 권고했다.',
    url: 'https://example.com/news/4',
    tags: ['보안', '기술'],
    category: '보안',
  },
]
