import type { Route } from '../types'

interface Props {
  route: Route
  isAdmin: boolean
  isLoggedIn: boolean
  navigate: (path: string) => void
}

export function NavRail({ route, isAdmin, navigate }: Props) {
  const items = [
    { path: '/', label: '뉴스', icon: <NewsIcon /> },
    { path: '/settings', label: '설정', icon: <SettingsIcon /> },
    ...(isAdmin ? [{ path: '/admin/pipeline', label: '관리', icon: <AdminIcon /> }] : []),
  ]

  const isActive = (path: string) => {
    if (path === '/admin/pipeline') return route.startsWith('/admin')
    return route === path
  }

  return (
    <nav
      className="sticky top-14 h-[calc(100vh-56px)] flex flex-col items-center py-3 border-r border-slate-200 bg-white shrink-0 hidden md:flex"
      style={{ width: 64 }}
      aria-label="주 탐색"
    >
      {items.map((item) => (
        <button
          key={item.path}
          onClick={() => navigate(item.path)}
          className={`w-12 flex flex-col items-center gap-1 py-2 px-1 rounded-lg transition-colors ${
            isActive(item.path)
              ? 'text-cyan-800 bg-cyan-50'
              : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'
          }`}
          title={item.label}
          aria-current={isActive(item.path) ? 'page' : undefined}
        >
          {item.icon}
          <span style={{ fontSize: 10, fontWeight: 500 }}>{item.label}</span>
        </button>
      ))}
    </nav>
  )
}

function NewsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 0-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2" />
      <path d="M18 14h-8" /><path d="M15 18h-5" /><path d="M10 6h8v4h-8V6Z" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function AdminIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect width="7" height="9" x="3" y="3" rx="1" />
      <rect width="7" height="5" x="14" y="3" rx="1" />
      <rect width="7" height="9" x="14" y="12" rx="1" />
      <rect width="7" height="5" x="3" y="16" rx="1" />
    </svg>
  )
}
