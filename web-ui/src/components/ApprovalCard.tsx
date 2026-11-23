import { useState } from 'react'
import { ShieldCheck, ShieldX, Lock, Hash } from 'lucide-react'
import type { ApprovalRequiredEvent } from '../types'
import { resolveApproval } from '../api'
import { formatTimestamp } from '../utils'

interface ApprovalCardProps {
  event: ApprovalRequiredEvent
  onResolved: (decision: 'approve' | 'reject') => void
}

export function ApprovalCard({ event, onResolved }: ApprovalCardProps) {
  const [loading, setLoading] = useState<'approve' | 'reject' | null>(null)
  const [resolved, setResolved] = useState<'approved' | 'rejected' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handle = async (decision: 'approve' | 'reject') => {
    setLoading(decision)
    setError(null)
    try {
      await resolveApproval(event.run_id, event.approval_id, decision)
      setResolved(decision === 'approve' ? 'approved' : 'rejected')
      onResolved(decision)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to resolve approval')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="rounded-lg border border-amber-500/50 bg-amber-950/30 p-4 shadow-lg shadow-amber-900/10">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <Lock className="h-4 w-4 text-amber-400" />
        <span className="text-amber-400 font-semibold text-sm">Human Approval Required</span>
        <span className="ml-auto text-xs text-slate-500">{formatTimestamp(event.timestamp)}</span>
      </div>

      {/* Tool Info */}
      <div className="mb-3 space-y-1">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500 w-20 shrink-0">Tool</span>
          <code className="text-cyan-300 bg-slate-800 px-2 py-0.5 rounded font-mono">{event.tool}</code>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-500 w-20 shrink-0">Server</span>
          <code className="text-slate-300 bg-slate-800 px-2 py-0.5 rounded font-mono">{event.server}</code>
        </div>
        <div className="flex items-start gap-2 text-xs">
          <span className="text-slate-500 w-20 shrink-0 mt-0.5">Expires</span>
          <span className="text-slate-300">{formatTimestamp(event.expires_at)}</span>
        </div>
      </div>

      {/* Payload */}
      <div className="mb-3">
        <p className="text-xs text-slate-500 mb-1.5">Proposed Payload</p>
        <pre className="text-xs bg-slate-900 border border-slate-700 rounded p-3 text-slate-200 overflow-auto max-h-40 font-mono leading-relaxed">
          {JSON.stringify(event.arguments, null, 2)}
        </pre>
      </div>

      {/* Hash */}
      <div className="flex items-center gap-2 mb-4 p-2 rounded bg-slate-900/50 border border-slate-700/50">
        <Hash className="h-3 w-3 text-slate-500 shrink-0" />
        <span className="text-xs text-slate-500">SHA-256</span>
        <code className="text-xs text-slate-400 font-mono truncate">{event.payload_hash}</code>
      </div>

      {error && (
        <p className="mb-3 text-xs text-red-400 bg-red-900/20 border border-red-700/30 rounded px-3 py-2">{error}</p>
      )}

      {resolved ? (
        <div className={`flex items-center gap-2 text-sm font-semibold justify-center py-2 rounded ${
          resolved === 'approved'
            ? 'text-emerald-400 bg-emerald-900/20'
            : 'text-red-400 bg-red-900/20'
        }`}>
          {resolved === 'approved' ? (
            <><ShieldCheck className="h-4 w-4" /> Approved — Executing</>
          ) : (
            <><ShieldX className="h-4 w-4" /> Rejected — No Action Taken</>
          )}
        </div>
      ) : (
        <div className="flex gap-3">
          <button
            onClick={() => handle('approve')}
            disabled={loading !== null}
            className="flex-1 flex items-center justify-center gap-2 py-2 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-sm font-semibold text-white transition-colors"
          >
            <ShieldCheck className="h-4 w-4" />
            {loading === 'approve' ? 'Approving…' : 'Approve'}
          </button>
          <button
            onClick={() => handle('reject')}
            disabled={loading !== null}
            className="flex-1 flex items-center justify-center gap-2 py-2 rounded bg-red-800 hover:bg-red-700 disabled:opacity-50 text-sm font-semibold text-white transition-colors"
          >
            <ShieldX className="h-4 w-4" />
            {loading === 'reject' ? 'Rejecting…' : 'Reject'}
          </button>
        </div>
      )}
    </div>
  )
}
