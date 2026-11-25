import {
  Play, CheckCircle, XCircle, Clock, AlertTriangle,
  Wrench, Cpu, FileText, ChevronDown, ChevronUp,
  Copy, Check, Zap, Shield, BarChart2, Activity
} from 'lucide-react'
import { useState } from 'react'
import type { AgentEvent, ApprovalResolvedEvent } from '../types'
import { ApprovalCard } from './ApprovalCard'
import { SecurityBanner } from './SecurityBanner'
import { Badge } from './Badge'
import { ToolStatusIcon } from './ui'
import { cn, formatMs, formatTimestamp, toolStatusBg, toolStatusColor } from '../utils'

interface EventTimelineProps {
  events: AgentEvent[]
  onApprovalResolved?: (decision: 'approve' | 'reject') => void
}

// Copy-to-clipboard button
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    }).catch(() => {})
  }
  return (
    <button
      onClick={copy}
      title="Copy to clipboard"
      aria-label="Copy output to clipboard"
      className="flex items-center gap-1 text-[10px] text-[var(--text-faint)] hover:text-[var(--text-muted)] transition-colors px-1.5 py-0.5 rounded hover:bg-[var(--surface-2)]"
    >
      {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

// Server badge pill
function ServerBadge({ server }: { server: string }) {
  const isOps = server === 'ops' || server.includes('ops')
  return (
    <span className={cn(
      'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium border',
      isOps
        ? 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20'
        : 'bg-teal-500/10   text-teal-300   border-teal-500/20'
    )}>
      {server}
    </span>
  )
}

function EventRow({ event, onApprovalResolved, resolvedApproval, runEnded }: {
  event: AgentEvent
  onApprovalResolved?: (decision: 'approve' | 'reject') => void
  resolvedApproval?: ApprovalResolvedEvent
  runEnded?: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  if (event.event_type === 'run_started') {
    return (
      <div className="flex items-center gap-3 py-2 fade-slide-in min-w-0">
        <Play className="h-4 w-4 text-cyan-400 shrink-0" />
        <span className="text-sm font-semibold text-cyan-400">Investigation Started</span>
        <span className="ml-auto text-xs text-[var(--text-faint)] font-mono tabular-nums shrink-0">{formatTimestamp(event.timestamp)}</span>
      </div>
    )
  }

  if (event.event_type === 'tool_started') {
    return (
      <div className="flex items-center gap-3 py-2 fade-slide-in min-w-0">
        <Wrench className={cn('h-3.5 w-3.5 shrink-0', event.is_mutating ? 'text-amber-400' : 'text-blue-400')} />
        <ServerBadge server={event.server} />
        <code className={cn('text-xs font-mono truncate min-w-0 flex-1', event.is_mutating ? 'text-amber-300' : 'text-blue-300')}>
          {event.tool}
        </code>
        {event.is_mutating && (
          <Badge variant="amber" className="text-[10px] shrink-0">mutating</Badge>
        )}
        <span className="ml-auto text-xs text-[var(--text-faint)] font-mono tabular-nums shrink-0">{formatTimestamp(event.timestamp)}</span>
      </div>
    )
  }

  if (event.event_type === 'tool_finished') {
    const statusVariant = event.status === 'ok' ? 'green' :
                          event.status === 'rejected' ? 'amber' :
                          event.status === 'blocked'  ? 'red'   : 'red'
    return (
      <div className={cn('rounded-lg border my-1 fade-slide-in overflow-hidden min-w-0', toolStatusBg(event.status))}>
        <div className="flex items-center gap-2 px-3 py-2.5 min-w-0">
          <ToolStatusIcon status={event.status} />
          <ServerBadge server={event.server} />
          <code className={cn('text-xs font-mono min-w-0 flex-1 truncate', toolStatusColor(event.status))}>{event.tool}</code>
          <Badge variant={statusVariant} className="text-[10px] shrink-0">
            {event.status.toUpperCase()}
          </Badge>
          <span className="text-xs text-[var(--text-faint)] font-mono tabular-nums shrink-0">
            {formatMs(event.duration_ms)}
          </span>
          <button
            onClick={() => setExpanded((p) => !p)}
            aria-expanded={expanded}
            aria-label="Toggle output"
            className="text-[var(--text-faint)] hover:text-[var(--text-muted)] ml-1 transition-colors shrink-0"
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>

        {event.injection_suspected && (
          <div className="px-3 pb-2">
            <SecurityBanner type="injection" />
          </div>
        )}

        {event.status === 'blocked' && (
          <div className="px-3 pb-2">
            <SecurityBanner type="blocked" tool={event.tool} detail={event.error ?? undefined} />
          </div>
        )}

        {expanded && (
          <div className="border-t border-[var(--border)] bg-[var(--surface)]">
            <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--border)]">
              <span className="text-micro">Output</span>
              <CopyButton text={event.output_preview} />
            </div>
            <pre className="text-xs font-mono text-[var(--text-muted)] p-3 overflow-auto max-h-56 leading-relaxed whitespace-pre-wrap break-words">
              {event.output_preview}
              {event.truncated && (
                <span className="text-[var(--text-faint)]"> … [TRUNCATED]</span>
              )}
            </pre>
          </div>
        )}
      </div>
    )
  }

  if (event.event_type === 'approval_required') {
    return (
      <div className="my-3 fade-slide-in">
        <ApprovalCard
          event={event}
          onResolved={onApprovalResolved ?? (() => {})}
          resolvedDecision={resolvedApproval?.decision}
          resolvedSource={resolvedApproval?.source ?? resolvedApproval?.approval_source}
          runEnded={runEnded}
        />
      </div>
    )
  }

  if (event.event_type === 'approval_resolved') {
    const source = event.source ?? event.approval_source ?? 'user'
    return (
      <div className="flex items-center gap-3 py-1.5 fade-slide-in">
        {event.decision === 'approved' ? (
          <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
        ) : (
          <XCircle className="h-4 w-4 text-amber-400 shrink-0" />
        )}
        <span className="text-sm text-[var(--text-muted)]">
          Approval{' '}
          <span className={event.decision === 'approved' ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
            {event.decision}
          </span>{' '}
          by <span className="text-[var(--text)]">{source}</span>
        </span>
      </div>
    )
  }

  if (event.event_type === 'llm_turn') {
    return (
      <div className="flex items-center gap-3 py-1.5 fade-slide-in">
        <Cpu className="h-3.5 w-3.5 text-violet-400 shrink-0" />
        <span className="text-xs text-[var(--text-faint)]">
          LLM turn {event.iteration}
          {event.tool_calls_count > 0 && (
            <span className="text-violet-400 ml-2">→ {event.tool_calls_count} call{event.tool_calls_count > 1 ? 's' : ''}</span>
          )}
          {event.latency_ms > 0 && (
            <span className="text-[var(--text-faint)] ml-2 font-mono tabular-nums">{formatMs(event.latency_ms)}</span>
          )}
        </span>
      </div>
    )
  }

  if (event.event_type === 'final_answer') {
    return (
      <div className="rounded-xl border-l-4 border-l-emerald-500/60 border border-emerald-500/15 bg-emerald-500/5 p-5 my-3 fade-slide-in min-w-0">
        <div className="flex items-center gap-2 mb-3 min-w-0">
          <FileText className="h-4 w-4 text-emerald-400 shrink-0" />
          <span className="text-sm font-semibold text-emerald-400">Investigation Complete</span>
          <span className="ml-auto text-xs text-[var(--text-faint)] font-mono tabular-nums shrink-0">{formatMs(event.duration_ms)} total</span>
        </div>
        <div className="text-sm text-[var(--text)] leading-relaxed whitespace-pre-wrap break-words min-w-0">
          {event.answer}
        </div>
        {event.tools_used.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5 pt-3 border-t border-[var(--border)]">
            <span className="text-micro mr-1">Tools used</span>
            {event.tools_used.map((t) => (
              <Badge key={t} variant="cyan"><code className="font-mono">{t}</code></Badge>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (event.event_type === 'run_stopped') {
    const isError = event.reason === 'error' || event.reason === 'max_iterations'
    return (
      <div className="flex items-center gap-3 py-2 fade-slide-in">
        {isError ? (
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
        ) : (
          <Clock className="h-4 w-4 text-[var(--text-faint)] shrink-0" />
        )}
        <span className={cn('text-sm', isError ? 'text-amber-400' : 'text-[var(--text-faint)]')}>
          Run stopped: <span className="font-mono">{event.reason}</span>
          {event.error && <span className="ml-2 text-red-400">{event.error}</span>}
        </span>
      </div>
    )
  }

  return null
}

// ─── Empty State ──────────────────────────────────────────────────
function EmptyState() {
  const capabilities = [
    { icon: <AlertTriangle className="h-4 w-4 text-red-400" />,   title: 'Root-cause analysis',    desc: 'Trace logs, errors, and metrics' },
    { icon: <Zap className="h-4 w-4 text-cyan-400" />,             title: 'Release readiness',      desc: 'Config checks, health, checklists' },
    { icon: <Shield className="h-4 w-4 text-violet-400" />,        title: 'Policy-checked actions', desc: 'Human-approved mutations only' },
  ]

  return (
    <div className="relative flex flex-col items-center justify-center py-20 text-center dot-grid rounded-xl overflow-hidden">
      {/* Ambient radial glow */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="h-64 w-64 rounded-full bg-cyan-500/5 blur-3xl" />
      </div>

      <div className="relative z-10 flex flex-col items-center gap-5">
        {/* Logo mark */}
        <div className="relative">
          <img
            src="/logo.png"
            alt="Agent Logo"
            className="h-20 w-20 object-contain opacity-70 drop-shadow-[0_0_20px_rgba(34,211,238,0.3)]"
            style={{ animation: 'pulse-live 4s ease-in-out infinite' }}
          />
        </div>

        <div>
          <h2 className="text-section-title text-[var(--text)] mb-1">Ready to investigate</h2>
          <p className="text-sm text-[var(--text-faint)] max-w-xs leading-relaxed">
            Ask a question, pick an example query, or start an investigation above
          </p>
        </div>

        {/* Capability tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2 max-w-lg w-full">
          {capabilities.map(({ icon, title, desc }) => (
            <div
              key={title}
              className="card p-3 text-left hover:border-[var(--border-strong)] transition-colors"
            >
              <div className="mb-2">{icon}</div>
              <p className="text-xs font-semibold text-[var(--text)] mb-0.5">{title}</p>
              <p className="text-[11px] text-[var(--text-faint)] leading-snug">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── Listening indicator (run started, no events yet) ─────────────
function ListeningState() {
  return (
    <div className="flex items-center gap-2 py-4 px-2 text-xs text-[var(--text-faint)]">
      <span className="h-2 w-2 rounded-full bg-cyan-400 pulse-live" />
      <span>Listening for events…</span>
    </div>
  )
}

export function EventTimeline({ events, onApprovalResolved }: EventTimelineProps) {
  const hasStarted = events.some(e => e.event_type === 'run_started')

  if (events.length === 0) {
    return <EmptyState />
  }

  if (hasStarted && events.length <= 1) {
    return (
      <>
        <EventRow event={events[0]} />
        <ListeningState />
      </>
    )
  }

  const resolvedByApprovalId = new Map<string, ApprovalResolvedEvent>()
  let runEnded = false
  for (const ev of events) {
    if (ev.event_type === 'approval_resolved') {
      resolvedByApprovalId.set(ev.approval_id, ev)
    } else if (ev.event_type === 'final_answer' || ev.event_type === 'run_stopped') {
      runEnded = true
    }
  }

  return (
    <div
      className="relative space-y-0.5 min-w-0"
      aria-live="polite"
      aria-label="Investigation events"
    >
      {/* Connecting timeline line */}
      <div className="absolute left-[7px] top-6 bottom-2 w-px bg-gradient-to-b from-cyan-500/30 via-[var(--border)] to-transparent pointer-events-none" />

      {events.map((ev) => (
        <div key={`${ev.run_id}-${ev.event_id}`} className="relative pl-5 min-w-0 overflow-hidden">
          <EventRow
            event={ev}
            onApprovalResolved={onApprovalResolved}
            resolvedApproval={
              ev.event_type === 'approval_required'
                ? resolvedByApprovalId.get(ev.approval_id)
                : undefined
            }
            runEnded={runEnded}
          />
        </div>
      ))}
    </div>
  )
}
