import { NavLink, Outlet, useNavigate } from 'react-router'

import { useLogout, useMe } from '../api/auth'
import { useHealth } from '../api/health'
import { Button } from './ui'

const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'text-sm font-medium text-indigo-700' : 'text-sm text-slate-600 hover:text-slate-900'

export function Layout() {
  const health = useHealth()
  const me = useMe()
  const logout = useLogout()
  const navigate = useNavigate()
  const apiStatus = health.isPending ? 'checking' : health.data?.status === 'ok' ? 'ok' : 'down'

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
          <NavLink to="/workspaces" className="font-semibold">
            Document Q&amp;A
          </NavLink>
          {me.data ? (
            <NavLink to="/workspaces" end className={linkClass}>
              Workspaces
            </NavLink>
          ) : null}
          <span className="ml-auto text-xs text-slate-500" data-testid="api-status">
            API: {apiStatus}
          </span>
          {me.data ? (
            <>
              <span className="text-sm text-slate-600" data-testid="current-user">
                {me.data.email}
              </span>
              <Button
                variant="secondary"
                disabled={logout.isPending}
                onClick={() => logout.mutate(undefined, { onSettled: () => navigate('/login') })}
              >
                Log out
              </Button>
            </>
          ) : me.isPending ? null : (
            <>
              <NavLink to="/login" className={linkClass}>
                Log in
              </NavLink>
              <NavLink to="/signup" className={linkClass}>
                Sign up
              </NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
