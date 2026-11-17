import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { errorMessage } from '../api/client'
import {
  useAttachLibrary,
  useDeleteDocument,
  useDetachLibrary,
  useDocuments,
  useLibrary,
  useRetryDocument,
  useUploadDocument,
} from '../api/documents'
import type { DocumentInfo } from '../api/types'
import { IngestionStatus } from '../components/IngestionStatus'
import { UploadDropzone } from '../components/UploadDropzone'
import { WorkspaceHeader } from '../components/WorkspaceHeader'
import { Button, ErrorText, Spinner } from '../components/ui'

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentsPage() {
  const { workspaceId = '' } = useParams()
  const documents = useDocuments(workspaceId)
  const upload = useUploadDocument(workspaceId)
  const [uploadErrors, setUploadErrors] = useState<string[]>([])

  async function onFiles(files: File[]) {
    setUploadErrors([])
    const results = await Promise.allSettled(files.map((f) => upload.mutateAsync(f)))
    setUploadErrors(
      results.flatMap((r, i) =>
        r.status === 'rejected' ? [`${files[i].name}: ${errorMessage(r.reason)}`] : [],
      ),
    )
  }

  const uploads = documents.data?.filter((d) => !d.is_library) ?? []
  const attached = documents.data?.filter((d) => d.is_library) ?? []
  const anyReady = documents.data?.some((d) => d.status === 'ready')

  return (
    <section>
      <WorkspaceHeader workspaceId={workspaceId} />
      <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-6">
          <UploadDropzone onFiles={onFiles} disabled={upload.isPending} />
          {upload.isPending ? <Spinner label="Uploading" /> : null}
          {uploadErrors.map((e) => (
            <ErrorText key={e}>{e}</ErrorText>
          ))}

          <div>
            <h2 className="text-sm font-semibold text-slate-700">Your uploads</h2>
            {documents.isPending ? <Spinner /> : null}
            <ErrorText>{documents.error ? errorMessage(documents.error) : null}</ErrorText>
            {documents.data && uploads.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No PDFs uploaded yet.</p>
            ) : null}
            <ul className="mt-2 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white empty:hidden">
              {uploads.map((d) => (
                <UploadRow key={d.id} workspaceId={workspaceId} doc={d} />
              ))}
            </ul>
          </div>

          {anyReady ? (
            <Link
              to={`/workspaces/${workspaceId}/chat`}
              className="inline-block rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Ask questions →
            </Link>
          ) : null}
        </div>

        <LibraryPanel workspaceId={workspaceId} attached={attached} />
      </div>
    </section>
  )
}

function UploadRow({ workspaceId, doc }: { workspaceId: string; doc: DocumentInfo }) {
  const retry = useRetryDocument(workspaceId)
  const remove = useDeleteDocument(workspaceId)
  const error = retry.error ?? remove.error
  const pages = doc.page_count ? ` · ${doc.page_count} pages` : ''

  return (
    <li className="px-4 py-3" data-testid="document-row" data-status={doc.status}>
      <div className="flex items-center gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium" title={doc.filename}>
            {doc.title}
          </p>
          <p className="text-xs text-slate-500">
            {formatSize(doc.size_bytes)}
            {pages}
          </p>
        </div>
        <IngestionStatus doc={doc} />
        {doc.status === 'failed' ? (
          <Button
            variant="secondary"
            onClick={() => retry.mutate(doc.id)}
            disabled={retry.isPending}
          >
            Retry
          </Button>
        ) : null}
        <Button
          variant="ghost"
          aria-label={`Delete ${doc.title}`}
          disabled={remove.isPending}
          onClick={() => {
            if (window.confirm(`Delete ${doc.filename}?`)) remove.mutate(doc.id)
          }}
        >
          Delete
        </Button>
      </div>
      {doc.status === 'failed' && doc.job?.error ? (
        <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-800" data-testid="doc-error">
          {doc.job.error}
          {doc.job.attempts > 1 ? ` (after ${doc.job.attempts} attempts)` : ''}
        </p>
      ) : null}
      {error ? <ErrorText>{errorMessage(error)}</ErrorText> : null}
    </li>
  )
}

function LibraryPanel({ workspaceId, attached }: { workspaceId: string; attached: DocumentInfo[] }) {
  const library = useLibrary()
  const attach = useAttachLibrary(workspaceId)
  const detach = useDetachLibrary(workspaceId)
  const attachedIds = new Set(attached.map((d) => d.id))
  const all = library.data ?? []
  const allAttached = all.length > 0 && all.every((d) => attachedIds.has(d.id))

  return (
    <aside className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">SEC filings library</h2>
        {all.length > 0 && !allAttached ? (
          <Button
            variant="secondary"
            onClick={() => attach.mutate(undefined)}
            disabled={attach.isPending}
          >
            Attach all
          </Button>
        ) : null}
      </div>
      <p className="text-xs text-slate-500">
        Shared, read-only 10-K filings. Attach them to ask questions across companies.
      </p>
      {library.isPending ? <Spinner /> : null}
      <ErrorText>{(library.error ?? attach.error ?? detach.error)?.message}</ErrorText>
      {library.data && all.length === 0 ? (
        <p className="text-sm text-slate-500">
          The library is empty. Run <code className="text-xs">make ingest-filings</code> to add
          the 10-K filings.
        </p>
      ) : null}
      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white empty:hidden">
        {all.map((d) => {
          const isAttached = attachedIds.has(d.id)
          return (
            <li key={d.id} className="flex items-center gap-2 px-3 py-2">
              <span className="min-w-0 flex-1 truncate text-sm">
                <span className="font-medium">{d.ticker}</span>{' '}
                <span className="text-slate-500">FY{d.fiscal_year}</span>
              </span>
              <Button
                variant={isAttached ? 'ghost' : 'secondary'}
                className="text-xs"
                onClick={() => (isAttached ? detach.mutate(d.id) : attach.mutate([d.id]))}
                disabled={attach.isPending || detach.isPending}
              >
                {isAttached ? 'Detach' : 'Attach'}
              </Button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
