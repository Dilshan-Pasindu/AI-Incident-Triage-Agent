import type { AgentEvent, HealthStatus, RunDetail, RunSummary } from './types'

const BASE = '/api'

export async function createRun(query: string, model = 'mock'): Promise<RunSummary> {
  const res = await fetch(`${BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, model }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function listRuns(limit = 50): Promise<RunSummary[]> {
  const res = await fetch(`${BASE}/runs?limit=${limit}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${BASE}/runs/${runId}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function resolveApproval(
  runId: string,
  approvalId: string,
  decision: 'approve' | 'reject'
): Promise<void> {
  const res = await fetch(`${BASE}/runs/${runId}/approvals/${approvalId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
}

export async function cancelRun(runId: string): Promise<void> {
  const res = await fetch(`${BASE}/runs/${runId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: 'User cancelled' }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function getHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getTraces(): Promise<Record<string, unknown>[]> {
  const res = await fetch(`${BASE}/traces?limit=100`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getBenchmarks(): Promise<{ content: string }> {
  const res = await fetch(`${BASE}/benchmarks`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

/** Opens an SSE stream and calls onEvent for each received event. Returns a close function. */
export function streamRunEvents(
  runId: string,
  onEvent: (ev: AgentEvent) => void,
  lastEventId?: number
): () => void {
  const url = lastEventId != null
    ? `${BASE}/runs/${runId}/events?last_event_id=${lastEventId}`
    : `${BASE}/runs/${runId}/events`

  const es = new EventSource(url)

  const eventTypes: AgentEvent['event_type'][] = [
    'run_started', 'llm_turn', 'tool_started', 'tool_finished',
    'approval_required', 'approval_resolved', 'final_answer', 'run_stopped',
  ]

  eventTypes.forEach((type) => {
    es.addEventListener(type, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as AgentEvent
        onEvent(data)
      } catch {
        // ignore parse errors
      }
    })
  })

  es.onerror = () => {
    es.close()
  }

  return () => es.close()
}
