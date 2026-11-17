import { Navigate, Outlet, useLocation } from 'react-router'

import { useMe } from '../api/auth'
import { errorMessage } from '../api/client'
import { ErrorText, Spinner } from './ui'

/** Renders child routes for signed-in users; sends everyone else to the login page. */
export function RequireAuth() {
  const me = useMe()
  const location = useLocation()
  if (me.isPending) return <Spinner />
  if (me.isError) return <ErrorText>Could not reach the server: {errorMessage(me.error)}</ErrorText>
  if (!me.data) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

/** Login and signup pages: already signed-in users go straight to their workspaces. */
export function GuestOnly() {
  const me = useMe()
  if (me.isPending) return <Spinner />
  if (me.data) return <Navigate to="/workspaces" replace />
  return <Outlet />
}
