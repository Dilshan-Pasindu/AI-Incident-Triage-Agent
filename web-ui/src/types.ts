// Core event types from the backend
export type EventType =
  | 'run_started'
  | 'llm_turn'
  | 'tool_started'
  | 'tool_finished'
  | 'approval_required'
  | 'approval_resolved'
  | 'final_answer'
  | 'run_stopped'

export type ToolStatus = 'ok' | 'error' | 'timeout' | 'rejected' | 'blocked' | 'invalid' | 'cancelled' | 'unknown'

export type RunState = 'pending' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'cancelled'

export interface BaseEvent {
  event_type: EventType
  run_id: string
  event_id: number
  timestamp: string
}

export interface RunStartedEvent extends BaseEvent {
  event_type: 'run_started'
  query: string
}

export interface LlmTurnEvent extends BaseEvent {
  event_type: 'llm_turn'
  iteration: number
  text_preview: string | null
  tool_calls_count: number
  latency_ms: number
}

export interface ToolStartedEvent extends BaseEvent {
  event_type: 'tool_started'
  iteration: number
  server: string
  tool: string
  tool_call_id: string
  arguments: Record<string, unknown>
  is_mutating: boolean
}

export interface ToolFinishedEvent extends BaseEvent {
  event_type: 'tool_finished'
  iteration: number
  server: string
  tool: string
  tool_call_id: string
  status: ToolStatus
  duration_ms: number
  output_preview: string
  truncated: boolean
  injection_suspected: boolean
  error: string | null
}

export interface ApprovalRequiredEvent extends BaseEvent {
  event_type: 'approval_required'
  approval_id: string
  tool_call_id: string
  tool: string
  server: string
  arguments: Record<string, unknown>
  payload_hash: string
  expires_at: string
}

export interface ApprovalResolvedEvent extends BaseEvent {
  event_type: 'approval_resolved'
  approval_id: string
  tool_call_id: string
  tool?: string
  decision: string
  source?: string
  approval_source?: string
}

export interface FinalAnswerEvent extends BaseEvent {
  event_type: 'final_answer'
  answer: string
  iterations: number
  tools_used: string[]
  duration_ms: number
}

export interface RunStoppedEvent extends BaseEvent {
  event_type: 'run_stopped'
  reason: string
  iterations: number
  error?: string
}

export type AgentEvent =
  | RunStartedEvent
  | LlmTurnEvent
  | ToolStartedEvent
  | ToolFinishedEvent
  | ApprovalRequiredEvent
  | ApprovalResolvedEvent
  | FinalAnswerEvent
  | RunStoppedEvent

export interface RunSummary {
  run_id: string
  query: string
  state: RunState
  created_at: string
  ended_at: string | null
  event_count: number
  tools_used: string[]
  result_preview: string | null
  error: string | null
  model: string | null
  has_pending_approval: boolean
}

export interface RunDetail extends RunSummary {
  events: AgentEvent[]
}

export interface HealthStatus {
  status: string
  mcp_servers: {
    ops: { name: string; health: string }
    fs: { name: string; health: string }
  }
  tools_count: number
  tools: string[]
  llm?: {
    provider: string
    model: string
  }
}
