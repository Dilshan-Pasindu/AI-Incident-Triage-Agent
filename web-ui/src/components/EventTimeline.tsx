import {
  Play, CheckCircle, XCircle, Clock, AlertTriangle,
  Wrench, Cpu, FileText, ChevronDown, ChevronUp, ShieldAlert
} from 'lucide-react'
import { useState } from 'react'
import type { AgentEvent } from '../types'
import { ApprovalCard } from './ApprovalCard'
import { SecurityBanner } from './SecurityBanner'
import { Badge } from './Badge'
import { cn, formatMs, formatTimestamp, toolStatusBg, toolStatusColor } from '../utils'

interface EventTimelineProps {
  events: AgentEvent[]
  onApprovalResolved?: (decision: 'approve' | 'reject') => void
}

function EventRow({ event, onApprovalResolved }: {
  event: AgentEvent
  onApprovalResolved?: (decision: 'approve' | 'reject') => void
}) {
  const [expanded, setExpanded] = useState(false)

  if (event.event_type === 'run_started') {
    return (
      <div className="flex items-center gap-3 py-2">
        <Play className="h-4 w-4 text-cyan-400 shrink-0" />
        <span className="text-cyan-400 text-sm font-semibold">Investigation Started</span>
        <span className="ml-auto text-xs text-slate-600">{formatTimestamp(event.timestamp)}</span>
      </div>
    )
  }

  if (event.event_type === 'tool_started') {
    return (
      <div className="flex items-center gap-3 py-2">
        <Wrench className={cn('h-4 w-4 shrink-0', event.is_mutating ? 'text-amber-400' : 'text-blue-400')} />
        <div className="flex-1 min-w-0">
          <span className="text-sm text-slate-200">
            <code className={cn('font-mono text-xs', event.is_mutating ? 'text-amber-300' : 'text-blue-300')}>
              {event.tool}
            </code>
          </span>
          {event.is_mutating && (
            <Badge variant="amber" className="ml-2">mutating</Badge>
          )}
        </div>
        <span className="ml-auto text-xs text-slate-600 shrink-0">{formatTimestamp(event.timestamp)}</span>
      </div>
    )
  }

  if (event.event_type === 'tool_finished') {
    return (
      <div className={cn('rounded border px-3 py-2 my-1', toolStatusBg(event.status))}>
        <div className="flex items-center gap-2">
          {event.status === 'ok' ? (
            <CheckCircle className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
          ) : (
            <XCircle className={cn('h-3.5 w-3.5 shrink-0', toolStatusColor(event.status))} />
          )}
          <code className={cn('text-xs font-mono', toolStatusColor(event.status))}>{event.tool}</code>
          <Badge variant={event.status === 'ok' ? 'green' : event.status === 'rejected' ? 'amber' : 'red'}>
            {event.status.toUpperCase()}
          </Badge>
          <span className="ml-auto text-xs text-slate-500">{formatMs(event.duration_ms)}</span>
          <button
            onClick={() => setExpanded((p) => !p)}
            className="text-slate-500 hover:text-slate-300 ml-1"
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>

        {event.injection_suspected && (
          <div className="mt-2">
            <SecurityBanner type="injection" />
          </div>
        )}

        {event.status === 'blocked' && (
          <div className="mt-2">
            <SecurityBanner type="blocked" tool={event.tool} detail={event.error ?? undefined} />
          </div>
        )}

        {expanded && (
          <pre className="mt-2 text-xs font-mono text-slate-300 bg-slate-900/50 rounded p-2 overflow-auto max-h-48 leading-relaxed whitespace-pre-wrap">
            {event.output_preview}
            {event.truncated && (
              <span className="text-slate-600"> … [TRUNCATED]</span>
            )}
          </pre>
        )}
      </div>
    )
  }

  if (event.event_type === 'approval_required') {
    return (
      <div className="my-2">
        <ApprovalCard
          event={event}
          onResolved={onApprovalResolved ?? (() => {})}
        />
      </div>
    )
  }

  if (event.event_type === 'approval_resolved') {
    return (
      <div className="flex items-center gap-3 py-1.5">
        {event.decision === 'approved' ? (
          <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
        ) : (
          <>
            <XCircle className="h-4 w-4 text-amber-400 shrink-0" />
          </>
        )}
        <span className="text-sm text-slate-300">
          Approval{' '}
          <span className={event.decision === 'approved' ? 'text-emerald-400' : 'text-amber-400'}>
            {event.decision}
          </span>{' '}
          by <span className="text-slate-400">{event.approval_source}</span>
        </span>
      </div>
    )
  }

  if (event.event_type === 'llm_turn') {
    return (
      <div className="flex items-center gap-3 py-1.5">
        <Cpu className="h-4 w-4 text-purple-400 shrink-0" />
        <span className="text-xs text-slate-400">
          LLM turn {event.iteration}
          {event.tool_calls_count > 0 && (
            <span className="text-purple-400 ml-2">→ {event.tool_calls_count} tool call{event.tool_calls_count > 1 ? 's' : ''}</span>
          )}
          {event.latency_ms > 0 && (
            <span className="text-slate-600 ml-2">{formatMs(event.latency_ms)}</span>
          )}
        </span>
      </div>
    )
  }

  if (event.event_type === 'final_answer') {
    return (
      <div className="rounded-lg border border-emerald-700/40 bg-emerald-950/20 p-4 my-2">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="h-4 w-4 text-emerald-400" />
          <span className="text-emerald-400 font-semibold text-sm">Investigation Complete</span>
          <span className="ml-auto text-xs text-slate-500">{formatMs(event.duration_ms)} total</span>
        </div>
        <pre className="text-sm text-slate-200 whitespace-pre-wrap font-sans leading-relaxed">
          {event.answer}
        </pre>
        {event.tools_used.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {event.tools_used.map((t) => (
              <Badge key={t} variant="cyan">{t}</Badge>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (event.event_type === 'run_stopped') {
    const isError = event.reason === 'error' || event.reason === 'max_iterations'
    return (
      <div className="flex items-center gap-3 py-2">
        {isError ? (
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
        ) : (
          <Clock className="h-4 w-4 text-slate-400 shrink-0" />
        )}
        <span className={cn('text-sm', isError ? 'text-amber-400' : 'text-slate-400')}>
          Run stopped: {event.reason}
          {event.error && <span className="ml-2 text-red-400">{event.error}</span>}
        </span>
      </div>
    )
  }

  return null
}

export function EventTimeline({ events, onApprovalResolved }: EventTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-500 text-sm gap-3">
        <img
          src="/logo.png"
          alt="Agent Logo"
          className="h-20 w-20 opacity-30 object-contain drop-shadow-[0_0_12px_rgba(6,182,212,0.25)] hover:opacity-60 transition-all duration-300"
        />
        <p className="font-mono text-xs text-slate-500">Waiting for investigation events to stream…</p>
      </div>
    )
  }

  return (
    <div className="space-y-0.5">
      {events.map((ev) => (
        <EventRow
          key={`${ev.run_id}-${ev.event_id}`}
          event={ev}
          onApprovalResolved={onApprovalResolved}
        />
      ))}
    </div>
  )
}
