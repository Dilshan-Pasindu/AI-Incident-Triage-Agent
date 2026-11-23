import { useEffect, useRef, useCallback, useState } from 'react'
import type { AgentEvent } from '../types'
import { streamRunEvents } from '../api'

interface UseRunStreamOptions {
  runId: string | null
  onEvent?: (ev: AgentEvent) => void
}

interface UseRunStreamResult {
  events: AgentEvent[]
  lastEventId: number | undefined
  close: () => void
}

export function useRunStream({ runId, onEvent }: UseRunStreamOptions): UseRunStreamResult {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const lastEventIdRef = useRef<number | undefined>(undefined)
  const closeRef = useRef<(() => void) | null>(null)

  const close = useCallback(() => {
    if (closeRef.current) {
      closeRef.current()
      closeRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!runId) return

    setEvents([])
    lastEventIdRef.current = undefined

    const handleEvent = (ev: AgentEvent) => {
      lastEventIdRef.current = ev.event_id
      setEvents((prev) => [...prev, ev])
      onEvent?.(ev)
    }

    closeRef.current = streamRunEvents(runId, handleEvent, lastEventIdRef.current)

    return () => {
      close()
    }
  }, [runId]) // eslint-disable-line

  return { events, lastEventId: lastEventIdRef.current, close }
}
