import { useDebounce } from 'use-debounce'

export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced] = useDebounce(value, delay)
  return debounced
}
