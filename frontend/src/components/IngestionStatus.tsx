import type { DocumentInfo } from '../api/types'

const stageLabels: Record<string, string> = {
  queued: 'Queued',
  parsing: 'Parsing',
  chunking: 'Chunking',
  embedding: 'Embedding',
  indexing: 'Indexing',
  done: 'Ready',
}

/** Status badge for a document, with a progress bar while it is being ingested. */
export function IngestionStatus({ doc }: { doc: DocumentInfo }) {
  const job = doc.job

  if (doc.status === 'ready') {
    return (
      <span
        className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"
        data-testid="doc-status"
      >
        Ready
      </span>
    )
  }
  if (doc.status === 'failed') {
    return (
      <span
        className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700"
        data-testid="doc-status"
      >
        Failed
      </span>
    )
  }

  const percent = Math.round(job?.progress ?? 0) // 0-100
  const stage = stageLabels[job?.stage ?? 'queued'] ?? job?.stage
  const retrying = job?.status === 'retrying'
  return (
    <div className="w-48" data-testid="doc-status">
      <div className="flex justify-between text-xs text-slate-600">
        <span>
          {retrying ? `Retrying (attempt ${(job?.attempts ?? 0) + 1})` : stage}
        </span>
        <span>{percent}%</span>
      </div>
      <div
        className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-200"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={`${doc.title} ingestion progress`}
      >
        <div
          className="h-full rounded-full bg-indigo-500 transition-[width] duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}
