/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 개발 서버(5173)에서 /api/v1 요청을 백엔드(8000)로 넘긴다.
    //
    // 프록시를 쓰는 이유: 브라우저가 보기에 프런트와 API가 같은 오리진이 되므로
    // CORS 설정 없이도 세션 쿠키(credentials:'include')가 그대로 전달된다.
    // 배포에서 nginx가 하는 일과 같은 구조라, 개발과 배포의 요청 경로가 어긋나지 않는다.
    //
    // 백엔드 주소를 바꿔야 하면 VITE_API_PROXY_TARGET 환경변수로 덮어쓴다.
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        // X-Forwarded-For / -Proto / -Host 를 붙인다. 배포에서 nginx가 하는 일과 같아서,
        // 하단 배포 정보줄의 XFF 표시를 개발에서도 실제로 검증할 수 있다.
        // 이 값이 비어 있으면 프록시가 클라이언트 IP를 넘기지 않는다는 뜻이다.
        xfwd: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
