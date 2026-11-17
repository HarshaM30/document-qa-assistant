import type { Citation } from '../api/types'
import { locationLabel } from '../lib/citations'

export function CitationChip({
  citation,
  active,
  onSelect,
}: {
  citation: Citation
  active: boolean
  onSelect: (c: Citation) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(citation)}
      data-testid="citation-chip"
      aria-pressed={active}
      title={`${citation.document_title} — ${locationLabel(citation)}`}
      className={`inline-flex max-w-xs items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
        active
          ? 'border-indigo-500 bg-indigo-50 text-indigo-800'
          : 'border-slate-300 bg-white text-slate-700 hover:border-indigo-400'
      }`}
    >
      <span className="font-semibold">[{citation.marker}]</span>
      <span className="truncate">{citation.document_title}</span>
      <span className="shrink-0 text-slate-500">{locationLabel(citation)}</span>
    </button>
  )
}
