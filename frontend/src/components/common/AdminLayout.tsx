import { Outlet } from 'react-router-dom'
import AdminTabs from './AdminTabs'

// /admin/* 하위 라우트 공통 셸. AppLayout(Header+NavRail) 안쪽에 한 번 더 중첩돼
// 관리자 화면 3개(파이프라인/LLM 사용량/보관 정책) 사이를 이동하는 탭을 보여준다.
export default function AdminLayout() {
  return (
    <div>
      <AdminTabs />
      <Outlet />
    </div>
  )
}
