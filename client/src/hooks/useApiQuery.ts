import { useCallback, useEffect, useRef, useState } from 'react'
import {
  type ApiError,
  type Envelope,
  type PaginatedMeta,
  toApiError,
} from '@/lib/api'

type QueryState<T> = {
  data: T | null
  meta: PaginatedMeta | null
  loading: boolean
  error: ApiError | null
}

/**
 * Fetches data whenever `key` changes. Keeps the previous result on screen
 * while the next request is in flight, so tables do not flicker on paging.
 */
export function useApiQuery<T>(
  key: string | null,
  fetcher: (signal: AbortSignal) => Promise<Envelope<T>>,
) {
  const [state, setState] = useState<QueryState<T>>({
    data: null,
    meta: null,
    loading: Boolean(key),
    error: null,
  })
  const [nonce, setNonce] = useState(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    if (!key) {
      setState({ data: null, meta: null, loading: false, error: null })
      return
    }

    const controller = new AbortController()
    setState(previous => ({ ...previous, loading: true, error: null }))

    fetcherRef
      .current(controller.signal)
      .then(response => {
        if (controller.signal.aborted) return
        setState({
          data: response.data,
          meta: response.meta ?? null,
          loading: false,
          error: null,
        })
      })
      .catch(error => {
        if (controller.signal.aborted) return
        setState(previous => ({
          ...previous,
          loading: false,
          error: toApiError(error),
        }))
      })

    return () => controller.abort()
  }, [key, nonce])

  const refetch = useCallback(() => setNonce(value => value + 1), [])

  return { ...state, refetch }
}
