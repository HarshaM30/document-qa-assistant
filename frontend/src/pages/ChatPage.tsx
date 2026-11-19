import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'

import { useChat } from '../api/chat'
import { useDocuments } from '../api/documents'
import type { Citation } from '../api/types'
import { ChatMessage } from '../components/ChatMessage'
import { CitationPanel } from '../components/CitationPanel'
import { WorkspaceHeader } from '../components/WorkspaceHeader'
import { Button, inputClass } from '../components/ui'

const MAX_QUESTION_CHARS = 2000

export function ChatPage() {
  const { workspaceId = '' } = useParams()
  // A fresh conversation (and history load) per workspace.
  return <Chat key={workspaceId} workspaceId={workspaceId} />
}

function Chat({ workspaceId }: { workspaceId: string }) {
  const { turns, ask, stop, streaming, historyLoading, historyError } = useChat(workspaceId)
  const documents = useDocuments(workspaceId)
  const [question, setQuestion] = useState('')
  const [selected, setSelected] = useState<Citation | null>(null)
  const bottom = useRef<HTMLDivElement>(null)

  const readyCount = documents.data?.filter((d) => d.status === 'ready').length ?? 0
  const lastAnswerLength = turns.at(-1)?.answer.length ?? 0

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [turns.length, lastAnswerLength])

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    const q = question.trim()
    if (!q || streaming) return
    setQuestion('')
    void ask(q)
  }

  return (
    <section>
      <WorkspaceHeader workspaceId={workspaceId} />
      <div className={`grid gap-6 ${selected ? 'lg:grid-cols-[1fr_24rem]' : ''}`}>
        <div className="flex min-h-[60vh] flex-col">
          <div className="flex-1 space-y-6" data-testid="chat-log">
            {historyError ? (
              <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-800">
                Earlier questions could not be loaded.
              </p>
            ) : null}
            {historyLoading ? (
              <p className="text-center text-sm text-slate-500">Loading conversation…</p>
            ) : turns.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 px-6 py-10 text-center text-sm text-slate-500">
                {documents.data && readyCount === 0 ? (
                  <>
                    No ready documents yet.{' '}
                    <Link
                      to={`/workspaces/${workspaceId}/documents`}
                      className="text-indigo-700 underline"
                    >
                      Upload a PDF or attach SEC filings
                    </Link>{' '}
                    first.
                  </>
                ) : (
                  'Ask a question about your documents. Answers cite the passages they come from.'
                )}
              </div>
            ) : null}
            {turns.map((t) => (
              <ChatMessage
                key={t.id}
                turn={t}
                activeChunkId={selected?.chunk_id ?? null}
                onSelectCitation={setSelected}
              />
            ))}
            <div ref={bottom} />
          </div>

          <form
            onSubmit={onSubmit}
            className="sticky bottom-0 mt-6 flex items-end gap-2 bg-slate-50 py-3"
          >
            <textarea
              className={`${inputClass} min-h-[2.75rem] resize-none`}
              rows={2}
              placeholder="Ask a question…"
              aria-label="Question"
              value={question}
              maxLength={MAX_QUESTION_CHARS}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  e.currentTarget.form?.requestSubmit()
                }
              }}
            />
            {streaming ? (
              <Button variant="secondary" onClick={stop} className="py-2">
                Stop
              </Button>
            ) : (
              <Button type="submit" disabled={!question.trim()} className="py-2">
                Ask
              </Button>
            )}
          </form>
        </div>

        {selected ? (
          <div className="lg:sticky lg:top-4 lg:self-start">
            <CitationPanel
              workspaceId={workspaceId}
              citation={selected}
              onClose={() => setSelected(null)}
            />
          </div>
        ) : null}
      </div>
    </section>
  )
}
