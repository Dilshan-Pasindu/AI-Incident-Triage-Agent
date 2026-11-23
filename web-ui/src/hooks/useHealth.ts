import { useEffect, useState, useCallback } from 'react'
import type { HealthStatus } from '../types'
import { getHealth } from '../api'

export function useHealth(intervalMs = 8000) {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const h = await getHealth()
      setHealth(h)
      setError(null)
    } catch (e) {
      setError('Backend unreachable')
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, intervalMs)
    return () => clearInterval(id)
  }, [refresh, intervalMs])

  return { health, error, refresh }
}
