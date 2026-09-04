import { useCallback, useEffect, useState } from 'react'

export function useAsyncResource<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    let active = true
    Promise.resolve()
      .then(() => {
        if (active) {
          setLoading(true)
          setError(null)
        }
        return loader()
      })
      .then((result) => {
        if (active) setData(result)
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason : new Error(String(reason)))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [loader, revision])

  const reload = useCallback(() => setRevision((value) => value + 1), [])
  return { data, loading, error, reload }
}
