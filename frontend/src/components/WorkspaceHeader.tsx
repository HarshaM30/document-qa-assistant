import { Link, NavLink } from 'react-router'

import { ApiError } from '../api/client'
import { useWorkspace } from '../api/workspaces'
import { ErrorText } from './ui'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `border-b-2 px-1 pb-2 text-sm ${
    isActive
      ? 'border-indigo-600 font-medium text-indigo-700'
      : 'border-transparent text-slate-600 hover:text-slate-900'
  }`

/** Workspace name with Documents / Chat tabs, or a not-found message. */
export function WorkspaceHeader({ workspaceId }: { workspaceId: string }) {
  const workspace = useWorkspace(workspaceId)
  if (workspace.error) {
    const missing = workspace.error instanceof ApiError && workspace.error.status === 404
    return (
      <div className="space-y-2">
        <ErrorText>{missing ? 'Workspace not found.' : workspace.error.message}</ErrorText>
        <Link to="/workspaces" className="text-sm text-indigo-700 underline">
          Back to workspaces
        </Link>
      </div>
    )
  }
  return (
    <div className="mb-6 border-b border-slate-200">
      <p className="text-xs text-slate-500">
        <Link to="/workspaces" className="hover:underline">
          Workspaces
        </Link>{' '}
        /
      </p>
      <h1 className="mt-1 text-2xl font-semibold" data-testid="workspace-name">
        {workspace.data?.name ?? ' '}
      </h1>
      <div className="mt-4 flex gap-6">
        <NavLink to={`/workspaces/${workspaceId}/documents`} className={tabClass}>
          Documents
        </NavLink>
        <NavLink to={`/workspaces/${workspaceId}/chat`} className={tabClass}>
          Chat
        </NavLink>
      </div>
    </div>
  )
}
