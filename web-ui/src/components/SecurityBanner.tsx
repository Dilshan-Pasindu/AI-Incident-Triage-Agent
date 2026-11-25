import { AlertTriangle, ShieldAlert, XCircle } from 'lucide-react'

interface SecurityBannerProps {
  type: 'injection' | 'blocked' | 'rejection'
  tool?: string
  detail?: string
}

export function SecurityBanner({ type, tool, detail }: SecurityBannerProps) {
  if (type === 'injection') {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/8 px-4 py-3 text-sm glow-danger">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
        <div>
          <p className="font-semibold text-red-400 mb-1 text-glow-red">⚠ Prompt Injection Detected &amp; Quarantined</p>
          <p className="text-red-300/80 text-xs leading-relaxed">
            Adversarial instruction payload was found in tool output. The content has been isolated inside{' '}
            <code className="font-mono bg-red-900/40 px-1 rounded">&lt;untrusted_tool_output&gt;</code>{' '}
            boundaries and treated as data only. No unauthorized actions were taken.
          </p>
        </div>
      </div>
    )
  }

  if (type === 'blocked') {
    return (
      <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/8 px-4 py-3 text-sm glow-warning">
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
        <div>
          <p className="font-semibold text-amber-400 mb-1">🚫 Path Traversal Blocked</p>
          <p className="text-amber-300/80 text-xs leading-relaxed">
            Filesystem access to{' '}
            <code className="font-mono bg-amber-900/40 px-1 rounded">{tool}</code>{' '}
            was blocked by canonical path confinement. Access is strictly limited to{' '}
            <code className="font-mono bg-amber-900/40 px-1 rounded">mock_data/workspace/</code>.
          </p>
          {detail && (
            <p className="mt-2 text-amber-200/60 text-xs font-mono bg-amber-950/50 p-2 rounded">{detail}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
      <div>
        <p className="font-semibold text-amber-400 mb-1">Operator Rejected Ticket Creation</p>
        <p className="text-amber-300/80 text-xs">
          The human-in-the-loop approval was denied. No state mutation was executed.
        </p>
      </div>
    </div>
  )
}
