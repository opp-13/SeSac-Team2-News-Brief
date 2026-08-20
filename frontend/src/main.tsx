import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './app/App'
import './index.css'

function renderApp() {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

// 기본값은 "실제 백엔드 호출"이다. VITE_USE_MSW=true 일 때만 목업이 뜬다 —
// 켜져 있으면 실제 API 응답을 가로채므로 백엔드 연동 확인이 불가능해진다.
// (프로덕션 빌드에서는 값과 무관하게 절대 시작하지 않는다.)
async function enableMocking() {
  if (!import.meta.env.DEV) return
  if (import.meta.env.VITE_USE_MSW !== 'true') return
  const { worker } = await import('./mocks/browser')
  await worker.start({ onUnhandledRequest: 'bypass' })
  console.info('[MSW] 목업 모드로 실행 중입니다. 실제 백엔드를 쓰려면 VITE_USE_MSW=false')
}

// worker.start()가 실패해도(서비스워커 등록 실패 등) 앱은 반드시 렌더링된다 —
// catch에서 렌더를 막지 않고 콘솔 경고만 남긴다.
enableMocking()
  .catch((err) => {
    console.warn('[MSW] 목업 서버 시작 실패 — 목업 없이 렌더링을 계속합니다.', err)
  })
  .finally(renderApp)
