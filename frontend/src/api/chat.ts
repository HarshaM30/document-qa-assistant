import { useCallback, useEffect, useRef, useState } from 'react'

import { readSse } from '../lib/sse'
import { ApiError, apiRequest, errorFromResponse } from './client'
import type { Citation } from './types'

export type AnswerState = 'streaming' | 'done' | 'refused' | 'stopped' | 'error'

export interface ChatTurn {
  id: string
  question: string
  answer: string
  state: AnswerState
  citations: Citation[]
  /** Shown under the answer: refusal message, rate-limit notice, or stream error. */
  notice: string | null
  rateLimited: boolean
  latencyMs: number | null
}

function rateLimitNotice(error: ApiError): string {
  const wait = error.retryAfter
  if (wait === null) return error.message
  const when = wait < 120 ? `${wait} s` : `${Math.ceil(wait / 60)} min`
  return `${error.message} You can ask again in ${when}.`
}

/** Chat turns for one workspace, plus ask/stop. Answers stream in token by token. */
export function useChat(workspaceId: string) {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const controller = useRef<AbortController | null>(null)

  const update = useCallback((id: string, patch: (t: ChatTurn) => Partial<ChatTurn>) => {
    setTurns((all) => all.map((t) => (t.id === id ? { ...t, ...patch(t) } : t)))
  }, [])

  // Abort an in-flight answer when leaving the page.
  useEffect(() => () => controller.current?.abort(), [])

  const ask = useCallback(
    async (question: string) => {
      controller.current?.abort()
      const abort = new AbortController()
      controller.current = abort
      const id = crypto.randomUUID()
      setTurns((all) => [
        ...all,
        {
          id,
          question,
          answer: '',
          state: 'streaming',
          citations: [],
          notice: null,
          rateLimited: false,
          latencyMs: null,
        },
      ])

      let finished = false
      try {
        const response = await apiRequest(`/workspaces/${workspaceId}/ask`, {
          method: 'POST',
          body: JSON.stringify({ question }),
          headers: { Accept: 'text/event-stream' },
          signal: abort.signal,
        })
        if (!response.ok) {
          const error = await errorFromResponse(response)
          const rateLimited = error.status === 429
          update(id, () => ({
            state: 'error',
            rateLimited,
            notice: rateLimited ? rateLimitNotice(error) : error.message,
          }))
          return
        }
        if (!response.body) throw new Error('The server sent an empty response.')

        for await (const { event, data } of readSse(response.body)) {
          const p = JSON.parse(data) as Record<string, unknown>
          if (event === 'token') {
            update(id, (t) => ({ answer: t.answer + String(p.text ?? '') }))
          } else if (event === 'refusal') {
            update(id, (t) => ({
              state: 'refused',
              answer: t.answer || String(p.message ?? ''),
              notice: null,
            }))
          } else if (event === 'citations') {
            update(id, () => ({ citations: (p.citations as Citation[]) ?? [] }))
          } else if (event === 'done') {
            finished = true
            update(id, (t) => ({
              state: t.state === 'refused' ? 'refused' : 'done',
              latencyMs: typeof p.latency_ms === 'number' ? p.latency_ms : null,
            }))
          } else if (event === 'error') {
            finished = true
            update(id, () => ({ state: 'error', notice: String(p.message ?? 'Answer failed.') }))
          }
        }
        if (!finished) {
          update(id, () => ({
            state: 'error',
            notice: 'The connection closed before the answer finished.',
          }))
        }
      } catch (error) {
        if (abort.signal.aborted) {
          update(id, (t) => (t.state === 'streaming' ? { state: 'stopped' } : {}))
        } else {
          // Network failure mid-stream: keep whatever text already arrived.
          update(id, () => ({
            state: 'error',
            notice: `Connection lost: ${error instanceof Error ? error.message : 'unknown error'}. The answer may be incomplete.`,
          }))
        }
      } finally {
        if (controller.current === abort) controller.current = null
      }
    },
    [workspaceId, update],
  )

  const stop = useCallback(() => controller.current?.abort(), [])
  const streaming = turns.some((t) => t.state === 'streaming')

  return { turns, ask, stop, streaming }
}
