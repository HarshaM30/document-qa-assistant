import { NavLink, Outlet } from 'react-router'

import { useHealth } from '../api/health'

const links = [
  { to: '/workspaces', label: 'Workspaces' },
  { to: '/login', label: 'Log in' },
  { to: '/signup', label: 'Sign up' },
]

export function Layout() {
  const health = useHealth()
  const apiStatus = health.isPending ? 'checking' : health.data?.status === 'ok' ? 'ok' : 'down'

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
          <span className="font-semibold">Document Q&amp;A</span>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                isActive ? 'text-sm font-medium text-indigo-700' : 'text-sm text-slate-600'
              }
            >
              {link.label}
            </NavLink>
          ))}
          <span className="ml-auto text-xs text-slate-500" data-testid="api-status">
            API: {apiStatus}
          </span>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
