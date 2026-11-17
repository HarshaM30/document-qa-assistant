import { usePassage } from '../api/documents'
import type { Citation } from '../api/types'
import { locationLabel } from '../lib/citations'
import { Button, ErrorText, Spinner } from './ui'

/** Side panel showing the full text of a cited passage, fetched on demand. */
export function CitationPanel({
  workspaceId,
  citation,
  onClose,
}: {
  workspaceId: string
  citation: Citation
  onClose: () => void
}) {
  const passage = usePassage(workspaceId, citation.chunk_id)
  return (
    <aside
      className="flex max-h-[calc(100vh-10rem)] flex-col rounded-lg border border-slate-200 bg-white"
      aria-label="Cited passage"
      data-testid="citation-panel"
    >
      <header className="flex items-start gap-3 border-b border-slate-200 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold text-indigo-700">Source [{citation.marker}]</p>
          <h2 className="truncate text-sm font-semibold" data-testid="citation-document">
            {citation.document_title}
          </h2>
          <p className="text-xs text-slate-500" data-testid="citation-location">
            {locationLabel(passage.data ?? citation)}
            {passage.data?.is_table ? ' · table' : ''}
          </p>
          {citation.item_code && citation.section_title ? (
            <p className="truncate text-xs text-slate-500">{citation.section_title}</p>
          ) : null}
        </div>
        <Button variant="ghost" onClick={onClose} aria-label="Close source panel">
          ✕
        </Button>
      </header>
      <div className="overflow-y-auto px-4 py-3">
        {passage.isPending ? <Spinner label="Loading passage" /> : null}
        {passage.error ? <ErrorText>{passage.error.message}</ErrorText> : null}
        {passage.data ? (
          <p
            className={`text-sm leading-relaxed whitespace-pre-wrap text-slate-800 ${
              passage.data.is_table ? 'font-mono text-xs' : ''
            }`}
            data-testid="passage-text"
          >
            {passage.data.text}
          </p>
        ) : null}
      </div>
    </aside>
  )
}
