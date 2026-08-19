// docs/figma-export/data/mockData.ts의 ALL_TAGS를 이관. GUEST_CATEGORIES(NewsFeedPage)와
// 달리 이 목록은 설정 화면뿐 아니라 회원가입 온보딩(design_plan.md §9)에서도 재사용될
// 예정이라 페이지 로컬이 아니라 공용 constants/로 뒀다. 서버가 관리하는 동적 데이터가
// 아니라 고정된 태그 집합이라 TanStack Query 대상이 아니다(§2 규칙2는 서버 데이터
// 목업 교체가 목적이지, 이런 고정 상수까지 겨냥하지 않는다고 판단했다).
export const ALL_TAGS = [
  'AI',
  '개발',
  '경제',
  '정치',
  '스타트업',
  '반도체',
  '글로벌',
  '규제',
  '보안',
  '모바일',
] as const
