// CI가 빌드 시 이 값을 주입한다 — 예: VITE_APP_VERSION=$(git rev-parse --short HEAD) npm run build
// 값이 없으면(로컬 개발 등) 'dev'로 표시한다.
export const FRONTEND_VERSION: string = import.meta.env.VITE_APP_VERSION || 'dev'
