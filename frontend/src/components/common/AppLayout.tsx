import { Outlet } from 'react-router-dom'
import Header from './Header'
import NavRail from './NavRail'

// docs/figma-export/App.tsx의 셸(Header + NavRail + main)을 이식.
// /login, /signup은 이 레이아웃 바깥의 별도 라우트라 여기 안 걸린다(원본 hideShell과 동일).
export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <div className="flex">
        <NavRail />
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
