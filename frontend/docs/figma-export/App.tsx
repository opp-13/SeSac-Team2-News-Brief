import { useState, useEffect, useCallback } from 'react'
import type { Route } from './types'
import { NewsFeedPage } from './pages/NewsFeedPage'
import { LoginPage } from './pages/LoginPage'
import { SignupPage } from './pages/SignupPage'
import { SettingsPage } from './pages/SettingsPage'
import { PipelinePage } from './pages/admin/PipelinePage'
import { LLMUsagePage } from './pages/admin/LLMUsagePage'
import { RetentionPage } from './pages/admin/RetentionPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { Header } from './components/Header'
import { NavRail } from './components/NavRail'

function parseRoute(hash: string): { route: Route; articleId: string | null } {
  const path = hash.replace('#', '') || '/'
  const articleMatch = path.match(/^\/articles\/(.+)$/)
  if (articleMatch) {
    return { route: '/', articleId: articleMatch[1] }
  }
  const validRoutes: Route[] = ['/', '/login', '/signup', '/settings', '/admin/pipeline', '/admin/llm-usage', '/admin/retention']
  const route = validRoutes.includes(path as Route) ? (path as Route) : '/404'
  return { route, articleId: null }
}

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [userTags, setUserTags] = useState<string[]>(['AI', '개발', '반도체'])
  const [route, setRoute] = useState<Route>('/')
  const [openArticleId, setOpenArticleId] = useState<string | null>(null)

  useEffect(() => {
    const update = () => {
      const { route, articleId } = parseRoute(window.location.hash)
      setRoute(route)
      setOpenArticleId(articleId)
    }
    update()
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])

  const navigate = useCallback((path: string) => {
    window.location.hash = path
  }, [])

  const handleLogin = (asAdmin = false) => {
    setIsLoggedIn(true)
    setIsAdmin(asAdmin)
    navigate('/')
  }

  const handleLogout = () => {
    setIsLoggedIn(false)
    setIsAdmin(false)
    navigate('/')
  }

  const openArticle = useCallback((id: string) => {
    navigate(`/articles/${id}`)
  }, [navigate])

  const closeArticle = useCallback(() => {
    navigate('/')
  }, [navigate])

  const isAdminRoute = route.startsWith('/admin')
  const hideShell = route === '/login' || route === '/signup'

  if (hideShell) {
    return (
      <div className="min-h-screen bg-slate-50">
        {route === '/login' && (
          <LoginPage navigate={navigate} onLogin={handleLogin} />
        )}
        {route === '/signup' && (
          <SignupPage navigate={navigate} onLogin={handleLogin} />
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50" style={{ fontFamily: "'Noto Sans KR', sans-serif" }}>
      <Header
        isLoggedIn={isLoggedIn}
        isAdmin={isAdmin}
        navigate={navigate}
        onLogout={handleLogout}
      />

      <div className="flex">
        <NavRail
          route={route}
          isAdmin={isAdmin}
          isLoggedIn={isLoggedIn}
          navigate={navigate}
        />

        <main className="flex-1 min-w-0">
          {route === '/' && (
            <NewsFeedPage
              isLoggedIn={isLoggedIn}
              userTags={userTags}
              openArticleId={openArticleId}
              onOpenArticle={openArticle}
              onCloseArticle={closeArticle}
              navigate={navigate}
            />
          )}
          {route === '/settings' && (
            <SettingsPage
              isLoggedIn={isLoggedIn}
              userTags={userTags}
              onSaveTags={setUserTags}
              navigate={navigate}
            />
          )}
          {route === '/admin/pipeline' && isAdmin && <PipelinePage />}
          {route === '/admin/llm-usage' && isAdmin && <LLMUsagePage />}
          {route === '/admin/retention' && isAdmin && <RetentionPage />}
          {route === '/404' && <NotFoundPage navigate={navigate} />}
          {isAdminRoute && !isAdmin && (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <p className="text-slate-500 text-[15px]">접근 권한이 없습니다.</p>
                <button
                  onClick={() => navigate('/')}
                  className="mt-4 text-cyan-800 text-[15px] underline"
                >
                  홈으로 돌아가기
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
