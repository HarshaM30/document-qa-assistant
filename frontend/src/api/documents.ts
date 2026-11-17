import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from './client'
import type { DocumentInfo, Passage } from './types'

const POLL_MS = 1500

export const documentsKey = (workspaceId: string) => ['documents', workspaceId] as const

const isPending = (d: DocumentInfo) => d.status === 'queued' || d.status === 'processing'

/** Documents visible to the workspace; polls while any of them is still being ingested. */
export function useDocuments(workspaceId: string) {
  return useQuery({
    queryKey: documentsKey(workspaceId),
    queryFn: () => apiFetch<DocumentInfo[]>(`/workspaces/${workspaceId}/documents`),
    staleTime: 0,
    refetchInterval: (query) => (query.state.data?.some(isPending) ? POLL_MS : false),
  })
}

export function useLibrary() {
  return useQuery({
    queryKey: ['library'],
    queryFn: () => apiFetch<DocumentInfo[]>('/library/documents'),
  })
}

function useDocumentMutation<V>(workspaceId: string, fn: (vars: V) => Promise<unknown>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => queryClient.invalidateQueries({ queryKey: documentsKey(workspaceId) }),
  })
}

export function useUploadDocument(workspaceId: string) {
  return useDocumentMutation(workspaceId, (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return apiFetch<DocumentInfo>(`/workspaces/${workspaceId}/documents`, {
      method: 'POST',
      body,
    })
  })
}

export function useRetryDocument(workspaceId: string) {
  return useDocumentMutation(workspaceId, (documentId: string) =>
    apiFetch<DocumentInfo>(`/workspaces/${workspaceId}/documents/${documentId}/retry`, {
      method: 'POST',
    }),
  )
}

export function useDeleteDocument(workspaceId: string) {
  return useDocumentMutation(workspaceId, (documentId: string) =>
    apiFetch<void>(`/workspaces/${workspaceId}/documents/${documentId}`, { method: 'DELETE' }),
  )
}

/** Attach library filings; `undefined` attaches the whole library. */
export function useAttachLibrary(workspaceId: string) {
  return useDocumentMutation(workspaceId, (documentIds: string[] | undefined) =>
    apiFetch<DocumentInfo[]>(`/workspaces/${workspaceId}/library`, {
      method: 'POST',
      body: JSON.stringify({ document_ids: documentIds ?? null }),
    }),
  )
}

export function useDetachLibrary(workspaceId: string) {
  return useDocumentMutation(workspaceId, (documentId: string) =>
    apiFetch<void>(`/workspaces/${workspaceId}/library/${documentId}`, { method: 'DELETE' }),
  )
}

export function usePassage(workspaceId: string, chunkId: string | null) {
  return useQuery({
    queryKey: ['passage', workspaceId, chunkId],
    queryFn: () => apiFetch<Passage>(`/workspaces/${workspaceId}/passages/${chunkId}`),
    enabled: chunkId !== null,
    staleTime: Infinity,
  })
}
