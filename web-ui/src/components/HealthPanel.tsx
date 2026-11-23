import { Server, Wrench, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react'
import type { HealthStatus } from '../types'
import { cn } from '../utils'

interface HealthPanelProps {
  health: HealthStatus | null
  error: string | null
  onRefresh: () => void
}

function ServerBadge({ name, health }: { name: string; health: string }) {
  const isHealthy = health === 'healthy'
  const isSuspect = health === 'suspect'

  return (
    <div className={cn(
      'flex items-center gap-2 rounded px-3 py-2 border text-xs',
      isHealthy
        ? 'bg-emerald-900/20 border-emerald-700/40'
        : isSuspect
          ? 'bg-amber-900/20 border-amber-700/40'
          : 'bg-red-900/20 border-red-700/40'
    )}>
      <span className={cn(
        'h-2 w-2 rounded-full',
        isHealthy ? 'bg-emerald-400 animate-pulse-slow' : isSuspect ? 'bg-amber-400' : 'bg-red-400'
      )} />
      <code className="text-slate-300">{name}</code>
      <span className={cn(
        'ml-auto font-mono uppercase text-xs',
        isHealthy ? 'text-emerald-400' : isSuspect ? 'text-amber-400' : 'text-red-400'
      )}>
        {health}
      </span>
    </div>
  )
}

export function HealthPanel({ health, error, onRefresh }: HealthPanelProps) {
  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Server className="h-4 w-4 text-slate-400" />
        <span className="text-sm font-semibold text-slate-300">MCP Infrastructure</span>
        <button
          onClick={onRefresh}
          className="ml-auto text-slate-600 hover:text-slate-400 transition-colors"
          title="Refresh"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {error ? (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-900/20 border border-red-700/30 rounded px-3 py-2">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      ) : health ? (
        <>
          <div className="space-y-2 mb-3">
            <ServerBadge name={health.mcp_servers.ops.name} health={health.mcp_servers.ops.health} />
            <ServerBadge name={health.mcp_servers.fs.name} health={health.mcp_servers.fs.health} />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Wrench className="h-3 w-3" />
            <span>{health.tools_count} tools registered</span>
            <CheckCircle2 className="h-3 w-3 text-emerald-500 ml-auto" />
            <span className="text-emerald-500">System Ready</span>
          </div>
        </>
      ) : (
        <div className="text-xs text-slate-600 animate-pulse">Connecting…</div>
      )}
    </div>
  )
}
