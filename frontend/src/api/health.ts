import { useQuery } from '@tanstack/react-query'

import { apiFetch } from './client'

export interface Health {
  status: 'ok' | 'degraded'
  version: string
  checks: Record<string, string>
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => apiFetch<Health>('/health'),
    retry: false,
  })
}
