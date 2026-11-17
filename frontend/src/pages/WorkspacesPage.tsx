import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { errorMessage } from '../api/client'
import type { Workspace } from '../api/types'
import {
  useCreateWorkspace,
  useDeleteWorkspace,
  useRenameWorkspace,
  useWorkspaces,
} from '../api/workspaces'
import { Button, ErrorText, Spinner, inputClass } from '../components/ui'

export function WorkspacesPage() {
  const workspaces = useWorkspaces()
  const create = useCreateWorkspace()
  const [name, setName] = useState('')

  function onCreate(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    create.mutate(name.trim(), { onSuccess: () => setName('') })
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Workspaces</h1>
        <p className="mt-1 text-sm text-slate-600">
          Each workspace has its own uploaded documents and can attach the shared SEC filings.
        </p>
      </div>

      <form onSubmit={onCreate} className="flex max-w-lg gap-2">
        <input
          className={inputClass}
          placeholder="New workspace name"
          aria-label="New workspace name"
          value={name}
          maxLength={200}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit" disabled={!name.trim() || create.isPending}>
          Create
        </Button>
      </form>
      <ErrorText>{create.error ? errorMessage(create.error) : null}</ErrorText>

      {workspaces.isPending ? <Spinner /> : null}
      <ErrorText>{workspaces.error ? errorMessage(workspaces.error) : null}</ErrorText>
      {workspaces.data?.length === 0 ? (
        <p className="text-sm text-slate-500">No workspaces yet. Create one to get started.</p>
      ) : null}
      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {workspaces.data?.map((w) => <WorkspaceRow key={w.id} workspace={w} />)}
      </ul>
    </section>
  )
}

function WorkspaceRow({ workspace }: { workspace: Workspace }) {
  const rename = useRenameWorkspace()
  const remove = useDeleteWorkspace()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(workspace.name)

  function onRename(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || name.trim() === workspace.name) {
      setEditing(false)
      return
    }
    rename.mutate({ id: workspace.id, name: name.trim() }, { onSuccess: () => setEditing(false) })
  }

  function onDelete() {
    if (window.confirm(`Delete "${workspace.name}" and all of its uploaded documents?`)) {
      remove.mutate(workspace.id)
    }
  }

  const error = rename.error ?? remove.error
  return (
    <li className="px-4 py-3" data-testid="workspace-row">
      <div className="flex items-center gap-3">
        {editing ? (
          <form onSubmit={onRename} className="flex flex-1 gap-2">
            <input
              className={inputClass}
              aria-label="Workspace name"
              value={name}
              maxLength={200}
              autoFocus
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setName(workspace.name)
                  setEditing(false)
                }
              }}
            />
            <Button type="submit" disabled={rename.isPending}>
              Save
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setName(workspace.name)
                setEditing(false)
              }}
            >
              Cancel
            </Button>
          </form>
        ) : (
          <>
            <Link
              to={`/workspaces/${workspace.id}/documents`}
              className="flex-1 font-medium text-slate-900 hover:text-indigo-700"
            >
              {workspace.name}
            </Link>
            <Link
              to={`/workspaces/${workspace.id}/chat`}
              className="text-sm text-indigo-700 hover:underline"
            >
              Chat
            </Link>
            <Button variant="ghost" onClick={() => setEditing(true)}>
              Rename
            </Button>
            <Button variant="danger" onClick={onDelete} disabled={remove.isPending}>
              Delete
            </Button>
          </>
        )}
      </div>
      {error ? (
        <div className="mt-1">
          <ErrorText>{errorMessage(error)}</ErrorText>
        </div>
      ) : null}
    </li>
  )
}
