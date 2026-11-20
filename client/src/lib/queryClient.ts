import { QueryClient } from '@tanstack/react-query'
import { ApiError } from '@/lib/api'

/**
 * Shared server-state cache.
 *
 * Requests are delegated to TanStack Query instead of a bespoke hook, so
 * caching, refetching and retries behave the same on every screen.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Directory data changes only when a CSV is imported; imports invalidate
      // the affected keys explicitly, so a short stale window avoids refetching
      // on every route visit or window focus.
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // 4xx answers (404, 422, ...) will not fix themselves by retrying.
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
        return failureCount < 2
      },
    },
    mutations: {
      retry: false,
    },
  },
})
