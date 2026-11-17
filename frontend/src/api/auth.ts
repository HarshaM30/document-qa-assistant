import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'

import { ApiError, apiFetch } from './client'
import type { User } from './types'

export const meKey = ['auth', 'me'] as const

/**
 * Switch the cached user and drop data cached for the previous one. The `me` query itself
 * is updated in place, not removed, so components already observing it re-render.
 */
function setSessionUser(queryClient: QueryClient, user: User | null) {
  queryClient.removeQueries({
    predicate: (q) => q.queryKey[0] !== 'health' && q.queryKey[0] !== meKey[0],
  })
  queryClient.setQueryData(meKey, user)
}

export interface Credentials {
  email: string
  password: string
}

/** The signed-in user, or null when there is no valid session. */
export function useMe() {
  return useQuery({
    queryKey: meKey,
    queryFn: async () => {
      try {
        return await apiFetch<User>('/auth/me')
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
    staleTime: 5 * 60_000,
    retry: false,
  })
}

function useAuthMutation(path: '/auth/login' | '/auth/signup') {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Credentials) =>
      apiFetch<User>(path, { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: (user) => setSessionUser(queryClient, user),
  })
}

export const useLogin = () => useAuthMutation('/auth/login')
export const useSignup = () => useAuthMutation('/auth/signup')

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>('/auth/logout', { method: 'POST' }),
    onSettled: () => setSessionUser(queryClient, null),
  })
}
