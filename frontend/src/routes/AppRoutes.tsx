import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '../components/common/AppLayout'
import AdminLayout from '../components/common/AdminLayout'
import AdminRoute from './AdminRoute'
import NewsFeedPage from '../pages/feed/NewsFeedPage'
import LoginPage from '../pages/auth/LoginPage'
import SignupPage from '../pages/auth/SignupPage'
import NotFoundPage from '../pages/common/NotFoundPage'
import PipelinePage from '../pages/admin/PipelinePage'
import RetentionPage from '../pages/admin/RetentionPage'
import SettingsPage from '../pages/common/SettingsPage'

// frontend/CLAUDE.md §5 화면 목록. /login, /signup은 레이아웃(Header/NavRail) 없이
// 렌더한다 (docs/figma-export/App.tsx의 hideShell 로직과 동일).
//
// "/"와 "/articles/:id"는 별도 컴포넌트 없이 같은 NewsFeedPage로 연결한다 — 목록과
// 모달을 한 컴포넌트가 다루므로, 이 둘을 같은 부모(AppLayout) 아래 형제 Route로 두면
// react-router의 background-location 트릭 없이도 리마운트 없이 동작한다. (스크롤 유지가
// 실제로 안 되면 그때 background-location 패턴으로 바꿔야 한다.)
//
// /admin/* — 관리자 화면 3개(파이프라인/LLM 사용량/보관 정책) 사이를 오갈 방법이
// 원본 프로토타입에도 없었다(NavRail·Header 둘 다 /admin/pipeline 하나만 가리켰음).
// 사용자 확인 후 AdminLayout(탭 바)으로 감싸기로 했다 — AdminRoute 가드도 개별 라우트
// 3개에 각각 걸지 않고 이 부모 라우트 하나에만 걸어 admin 권한 체크가 한 번만 일어난다.
// 빈 /admin 진입은 /admin/pipeline으로 보낸다(NavRail 관리 아이콘의 기본 목적지와 동일).
export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<NewsFeedPage />} />
        <Route path="/articles/:id" element={<NewsFeedPage />} />
        <Route path="/settings" element={<SettingsPage />} />

        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminLayout />
            </AdminRoute>
          }
        >
          <Route index element={<Navigate to="/admin/pipeline" replace />} />
          <Route path="pipeline" element={<PipelinePage />} />
          <Route path="retention" element={<RetentionPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>

      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
    </Routes>
  )
}
