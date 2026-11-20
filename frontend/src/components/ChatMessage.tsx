import type { ChatTurn } from '../api/chat'
import type { Citation } from '../api/types'
import { CitationChip } from './CitationChip'

// [1], [1, 3], and gpt-oss's line-referenced form [1†L9-L10]
const MARKER = /(\[\s*\d+(?:\s*,\s*\d+)*\s*(?:†[^\]]*)?\])/g

// Models sometimes emphasise figures with Markdown bold (**$254,098 million**).
const BOLD = /\*\*([^*\n]+?)\*\*/g

/** Answer text with **bold** spans and [n] markers rendered as clickable superscripts. */
function AnswerText({
  text,
  citations,
  onSelect,
}: {
  text: string
  citations: Citation[]
  onSelect: (c: Citation) => void
}) {
  const byMarker = new Map(citations.map((c) => [c.marker, c]))
  const withMarkers = (segment: string, key: string) =>
    segment.split(MARKER).map((part, i) => {
      if (i % 2 === 0) return part
      const numbers = part.slice(1, -1).split('†')[0].split(',').map((n) => Number(n.trim()))
      return numbers.map((n, j) => {
        const citation = byMarker.get(n)
        if (!citation)
          return (
            <sup key={`${key}-${i}-${j}`} className="text-slate-400">
              [{n}]
            </sup>
          )
        return (
          <sup key={`${key}-${i}-${j}`}>
            <button
              type="button"
              className="font-semibold text-indigo-700 hover:underline"
              onClick={() => onSelect(citation)}
              aria-label={`Show source ${n}`}
            >
              [{n}]
            </button>
          </sup>
        )
      })
    })
  return (
    <>
      {text.split(BOLD).map((part, i) =>
        i % 2 === 0 ? (
          withMarkers(part, String(i))
        ) : (
          <strong key={i} className="font-semibold">
            {withMarkers(part, String(i))}
          </strong>
        ),
      )}
    </>
  )
}

export function ChatMessage({
  turn,
  activeChunkId,
  onSelectCitation,
}: {
  turn: ChatTurn
  activeChunkId: string | null
  onSelectCitation: (c: Citation) => void
}) {
  const refused = turn.state === 'refused'
  return (
    <article className="space-y-3" data-testid="chat-turn" data-state={turn.state}>
      <div className="flex justify-end">
        <p className="max-w-[80%] rounded-lg bg-indigo-600 px-4 py-2 text-sm whitespace-pre-wrap text-white">
          {turn.question}
        </p>
      </div>
      <div
        className={`rounded-lg border px-4 py-3 text-sm leading-relaxed ${
          refused ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-slate-200 bg-white'
        }`}
      >
        {refused ? (
          <p className="mb-1 text-xs font-semibold tracking-wide text-amber-700 uppercase">
            Not in your documents
          </p>
        ) : null}
        <div className="whitespace-pre-wrap" data-testid="answer-text">
          <AnswerText text={turn.answer} citations={turn.citations} onSelect={onSelectCitation} />
          {turn.state === 'streaming' ? (
            <span
              className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-slate-400 align-text-bottom"
              aria-label="Answer streaming"
            />
          ) : null}
        </div>
        {turn.state === 'stopped' ? (
          <p className="mt-2 text-xs text-slate-500">Stopped.</p>
        ) : null}
        {turn.notice ? (
          <p
            role="alert"
            data-testid={turn.rateLimited ? 'rate-limit-notice' : 'answer-error'}
            className={`mt-2 rounded-md px-3 py-2 text-xs ${
              turn.rateLimited ? 'bg-amber-50 text-amber-800' : 'bg-red-50 text-red-800'
            }`}
          >
            {turn.notice}
          </p>
        ) : null}
        {turn.citations.length ? (
          <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
            {turn.citations.map((c) => (
              <CitationChip
                key={c.marker}
                citation={c}
                active={c.chunk_id === activeChunkId}
                onSelect={onSelectCitation}
              />
            ))}
          </div>
        ) : null}
      </div>
    </article>
  )
}
