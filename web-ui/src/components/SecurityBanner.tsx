import { AlertTriangle, ShieldAlert, XCircle } from 'lucide-react'

interface SecurityBannerProps {
  type: 'injection' | 'blocked' | 'rejection'
  tool?: string
  detail?: string
}

export function SecurityBanner({ type, tool, detail }: SecurityBannerProps) {
  if (type === 'injection') {
    return (
      <div className="flex items-start gap-3 rounded-md border border-red-700/50 bg-red-950/40 px-4 py-3 text-sm">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
        <div>
          <p className="font-semibold text-red-400 text-glow-red">⚠ Prompt Injection Detected &amp; Quarantined</p>
          <p className="mt-0.5 text-red-300/80 text-xs">
            Adversarial instruction payload was found in tool output. The content has been isolated inside{' '}
            <code className="font-mono bg-red-900/40 px-1 rounded">&lt;untrusted_tool_output&gt;</code> boundaries
            and treated as data only. No unauthorized actions were taken.
          </p>
        </div>
      </div>
    )
  }

  if (type === 'blocked') {
    return (
      <div className="flex items-start gap-3 rounded-md border border-orange-700/50 bg-orange-950/40 px-4 py-3 text-sm">
        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-orange-400" />
        <div>
          <p className="font-semibold text-orange-400">🚫 Path Traversal Blocked</p>
          <p className="mt-0.5 text-orange-300/80 text-xs">
            Filesystem access to <code className="font-mono bg-orange-900/40 px-1 rounded">{tool}</code> was
            blocked by canonical path confinement. Access is strictly limited to{' '}
            <code className="font-mono bg-orange-900/40 px-1 rounded">mock_data/workspace/</code>.
          </p>
          {detail && <p className="mt-1 text-orange-200/60 text-xs font-mono">{detail}</p>}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 rounded-md border border-amber-700/50 bg-amber-950/30 px-4 py-3 text-sm">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
      <div>
        <p className="font-semibold text-amber-400">Operator Rejected Ticket Creation</p>
        <p className="mt-0.5 text-amber-300/80 text-xs">
          The human-in-the-loop approval was denied. No state mutation was executed.
        </p>
      </div>
    </div>
  )
}
