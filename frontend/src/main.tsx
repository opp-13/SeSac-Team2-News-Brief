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

async function enableMocking() {
  if (!import.meta.env.DEV) return
  const { worker } = await import('./mocks/browser')
  await worker.start({ onUnhandledRequest: 'bypass' })
}

// worker.start()가 실패해도(서비스워커 등록 실패 등) 앱은 반드시 렌더링된다 —
// catch에서 렌더를 막지 않고 콘솔 경고만 남긴다.
enableMocking()
  .catch((err) => {
    console.warn('[MSW] 목업 서버 시작 실패 — 목업 없이 렌더링을 계속합니다.', err)
  })
  .finally(renderApp)
