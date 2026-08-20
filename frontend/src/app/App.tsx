import { useLayoutEffect, useRef, useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import AppRoutes from '../routes/AppRoutes'
import DeployInfoFooter from '../components/common/DeployInfoFooter'

const queryClient = new QueryClient()

export default function App() {
  // 하단 배포 정보 바를 fixed로 고정하면서, 그 높이만큼 본문에 여백을 줘서 마지막
  // 콘텐츠(예: 피드의 "더 보기" 버튼)가 바 밑에 가려지지 않게 한다. 서버IP/서버명/
  // 클라이언트IP/XFF 텍스트가 좁은 화면에서 줄바꿈될 수 있어 고정 px 값 대신
  // ResizeObserver로 실제 렌더 높이를 측정한다.
  const footerRef = useRef<HTMLDivElement>(null)
  const [footerHeight, setFooterHeight] = useState(0)

  useLayoutEffect(() => {
    const el = footerRef.current
    if (!el) return
    const update = () => setFooterHeight(el.offsetHeight)
    update()
    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div style={{ paddingBottom: footerHeight }}>
          <AppRoutes />
        </div>
        <div ref={footerRef} className="fixed bottom-0 inset-x-0 z-40">
          <DeployInfoFooter />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
