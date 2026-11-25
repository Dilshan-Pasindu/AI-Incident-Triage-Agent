import { useState } from 'react'
import { ShieldCheck, ShieldX, Lock, Hash, ChevronDown, ChevronUp, Clock } from 'lucide-react'
import type { ApprovalRequiredEvent } from '../types'
import { resolveApproval } from '../api'
import { formatTimestamp } from '../utils'

interface ApprovalCardProps {
  event: ApprovalRequiredEvent
  onResolved: (decision: 'approve' | 'reject') => void
  resolvedDecision?: string
  resolvedSource?: string
  runEnded?: boolean
}

export function ApprovalCard({
  event,
  onResolved,
  resolvedDecision,
  resolvedSource,
  runEnded,
}: ApprovalCardProps) {
  const [loading, setLoading] = useState<'approve' | 'reject' | null>(null)
  const [localResolved, setLocalResolved] = useState<'approved' | 'rejected' | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handle = async (decision: 'approve' | 'reject') => {
    setLoading(decision)
    setError(null)
    try {
      await resolveApproval(event.run_id, event.approval_id, decision)
      setLocalResolved(decision === 'approve' ? 'approved' : 'rejected')
      onResolved(decision)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to resolve approval')
    } finally {
      setLoading(null)
    }
  }

  const effectiveDecision = localResolved ?? resolvedDecision ?? (runEnded ? 'closed' : null)

  // Resolved / historical read-only audit card
  if (effectiveDecision) {
    const isApproved = effectiveDecision === 'approved'
    const isRejected = effectiveDecision === 'rejected'
    const style = isApproved
      ? 'bg-emerald-500/8 border-emerald-500/20 text-emerald-400'
      : isRejected
        ? 'bg-red-500/8 border-red-500/20 text-red-400'
        : 'bg-[var(--surface-2)] border-[var(--border)] text-[var(--text-muted)]'

    const label = isApproved
      ? 'Approved'
      : isRejected
        ? 'Rejected'
        : effectiveDecision === 'expired'
          ? 'Expired'
          : 'Closed'

    return (
      <div className={`rounded-xl border px-4 py-3 text-xs fade-slide-in min-w-0 ${style}`}>
        <div className="flex items-center gap-2.5 min-w-0">
          {isApproved ? (
            <ShieldCheck className="h-4 w-4 shrink-0" />
          ) : isRejected ? (
            <ShieldX className="h-4 w-4 shrink-0" />
          ) : (
            <Clock className="h-4 w-4 shrink-0" />
          )}
          <span className="font-semibold shrink-0">{label}</span>
          {resolvedSource && (
            <span className="text-[11px] opacity-80 shrink-0">via {resolvedSource}</span>
          )}
          <code className="font-mono text-cyan-300/90 truncate min-w-0 ml-1">{event.tool}</code>
          <button
            type="button"
            onClick={() => setShowDetails((p) => !p)}
            aria-expanded={showDetails}
            className="ml-auto flex items-center gap-1 text-[11px] text-[var(--text-faint)] hover:text-[var(--text-muted)] shrink-0"
          >
            {showDetails ? 'Hide details' : 'Details'}
            {showDetails ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>

        {showDetails && (
          <div className="mt-3 pt-3 border-t border-[var(--border)] space-y-2 text-[var(--text-muted)]">
            <pre className="text-xs bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3 overflow-auto max-h-44 font-mono leading-relaxed whitespace-pre-wrap break-words">
              {JSON.stringify(event.arguments, null, 2)}
            </pre>
            <div className="flex items-center gap-2 text-[11px] text-[var(--text-faint)] min-w-0">
              <Hash className="h-3 w-3 shrink-0" />
              <span className="shrink-0">SHA-256</span>
              <code className="font-mono truncate min-w-0">{event.payload_hash}</code>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-violet-500/40 bg-violet-500/5 p-5 glow-violet fade-slide-in min-w-0">
      {/* Header */}
      <div className="flex items-center gap-2.5 mb-4 min-w-0">
        <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-violet-500/15 border border-violet-500/25 shrink-0">
          <Lock className="h-4 w-4 text-violet-400" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-violet-300">Human Approval Required</p>
          <p className="text-xs text-[var(--text-faint)] font-mono tabular-nums mt-0.5">{formatTimestamp(event.timestamp)}</p>
        </div>
        <span className="ml-auto flex items-center gap-1.5 text-[11px] font-medium text-violet-400 shrink-0">
          <span className="h-2 w-2 rounded-full bg-violet-400 pulse-live" />
          Pending
        </span>
      </div>

      {/* Tool Info */}
      <div className="mb-4 space-y-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] p-3">
        {[
          { label: 'Tool',    value: <code className="font-mono text-cyan-300 break-all">{event.tool}</code> },
          { label: 'Server',  value: <code className="font-mono text-[var(--text-muted)]">{event.server}</code> },
          { label: 'Expires', value: <span className="text-[var(--text-muted)] font-mono tabular-nums">{formatTimestamp(event.expires_at)}</span> },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-start gap-3 text-xs">
            <span className="text-[var(--text-faint)] w-16 shrink-0 font-medium pt-0.5">{label}</span>
            <div className="min-w-0 flex-1">{value}</div>
          </div>
        ))}
      </div>

      {/* Payload */}
      <div className="mb-4">
        <p className="text-micro mb-2">Proposed Payload</p>
        <pre className="text-xs bg-[var(--surface)] border border-[var(--border)] rounded-lg p-3 text-[var(--text-muted)] overflow-auto max-h-44 font-mono leading-relaxed whitespace-pre-wrap break-words">
          {JSON.stringify(event.arguments, null, 2)}
        </pre>
      </div>

      {/* Hash */}
      <div className="flex items-center gap-2 mb-5 p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border)] min-w-0">
        <Hash className="h-3 w-3 text-[var(--text-faint)] shrink-0" />
        <span className="text-xs text-[var(--text-faint)] font-medium shrink-0">SHA-256</span>
        <code className="text-xs text-[var(--text-muted)] font-mono truncate min-w-0">{event.payload_hash}</code>
      </div>

      {error && (
        <p className="mb-4 text-xs text-red-400 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => handle('reject')}
          disabled={loading !== null}
          className="btn-danger flex-1 flex items-center justify-center gap-2 py-2.5 text-sm"
        >
          <ShieldX className="h-4 w-4" />
          {loading === 'reject' ? 'Rejecting…' : 'Reject'}
        </button>
        <button
          onClick={() => handle('approve')}
          disabled={loading !== null}
          className="btn-primary flex-1 flex items-center justify-center gap-2 py-2.5 text-sm"
        >
          <ShieldCheck className="h-4 w-4" />
          {loading === 'approve' ? 'Approving…' : 'Approve'}
        </button>
      </div>
    </div>
  )
}
