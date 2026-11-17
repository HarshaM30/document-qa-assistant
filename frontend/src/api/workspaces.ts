import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from './client'
import type { Workspace } from './types'

export const workspacesKey = ['workspaces'] as const

export function useWorkspaces() {
  return useQuery({
    queryKey: workspacesKey,
    queryFn: () => apiFetch<Workspace[]>('/workspaces'),
  })
}

export function useWorkspace(id: string) {
  return useQuery({
    queryKey: [...workspacesKey, id],
    queryFn: () => apiFetch<Workspace>(`/workspaces/${id}`),
    retry: false,
  })
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<Workspace>('/workspaces', { method: 'POST', body: JSON.stringify({ name }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workspacesKey }),
  })
}

export function useRenameWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      apiFetch<Workspace>(`/workspaces/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workspacesKey }),
  })
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/workspaces/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: workspacesKey }),
  })
}
