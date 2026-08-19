import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { colors } from '../constants/theme'

interface AdminRouteProps {
  children: ReactNode
}

// docs/figma-export/App.tsx의 "isAdminRoute && !isAdmin" 분기를 라우트 가드로 이식.
export default function AdminRoute({ children }: AdminRouteProps) {
  const navigate = useNavigate()
  const { isAdmin, isLoading } = useAuth()

  // 세션 조회 중엔 "권한 없음"을 확정해서 보여주지 않는다 (깜빡임 방지).
  if (isLoading) {
    return <div className="h-96 animate-pulse bg-slate-50" />
  }

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-slate-500 text-[15px]">접근 권한이 없습니다.</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 text-[15px] underline"
            style={{ color: colors.accent }}
          >
            홈으로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
