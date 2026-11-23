import { Server, Wrench, AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react'
import type { HealthStatus } from '../types'
import { cn } from '../utils'
import { Card, SectionHeader, IconButton } from './ui'
import { Badge } from './Badge'

interface HealthPanelProps {
  health: HealthStatus | null
  error: string | null
  onRefresh: () => void
}

function ServerRow({ name, health, toolCount }: { name: string; health: string; toolCount?: number }) {
  const isHealthy = health === 'healthy'
  const isSuspect = health === 'suspect'
  const variant = isHealthy ? 'green' : isSuspect ? 'amber' : 'red'

  return (
    <div className={cn(
      'flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors',
      isHealthy  ? 'bg-emerald-500/5 border-emerald-500/15' :
      isSuspect  ? 'bg-amber-500/5  border-amber-500/15'   :
                   'bg-red-500/5    border-red-500/15'
    )}>
      <span className={cn(
        'h-2 w-2 rounded-full shrink-0',
        isHealthy  ? 'bg-emerald-400 pulse-live' :
        isSuspect  ? 'bg-amber-400'              :
                     'bg-red-400'
      )} />
      <code className="text-xs text-[var(--text)] font-mono flex-1 truncate">{name}</code>
      {toolCount !== undefined && (
        <span className="text-[10px] text-[var(--text-faint)] font-medium shrink-0">
          {toolCount} tools
        </span>
      )}
      <Badge variant={variant} className="shrink-0 text-[10px]">
        {health}
      </Badge>
    </div>
  )
}

export function HealthPanel({ health, error, onRefresh }: HealthPanelProps) {
  const allHealthy = health &&
    health.mcp_servers.ops.health === 'healthy' &&
    health.mcp_servers.fs.health === 'healthy'

  return (
    <Card className="p-4">
      <SectionHeader
        icon={<Server className="h-3.5 w-3.5" />}
        label="MCP Infrastructure"
        action={
          <IconButton onClick={onRefresh} title="Refresh health" aria-label="Refresh MCP health">
            <RefreshCw className="h-3.5 w-3.5" />
          </IconButton>
        }
      />

      {error ? (
        <div className="flex items-start gap-2.5 rounded-lg border border-red-500/20 bg-red-500/8 px-3 py-2.5 text-xs text-red-400">
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      ) : health ? (
        <>
          <div className="space-y-2 mb-3">
            <ServerRow
              name={health.mcp_servers.ops.name}
              health={health.mcp_servers.ops.health}
              toolCount={Math.round(health.tools_count * 0.23)}
            />
            <ServerRow
              name={health.mcp_servers.fs.name}
              health={health.mcp_servers.fs.health}
              toolCount={Math.round(health.tools_count * 0.77)}
            />
          </div>

          {/* Footer */}
          <div className="flex items-center gap-2 pt-2.5 border-t border-[var(--border)]">
            <Wrench className="h-3 w-3 text-[var(--text-faint)]" />
            <span className="text-[11px] text-[var(--text-faint)] tabular-nums">
              {health.tools_count} tools
            </span>
            <div className="ml-auto flex items-center gap-1.5">
              {allHealthy ? (
                <>
                  <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                  <span className="text-[11px] text-emerald-400 font-medium">All systems operational</span>
                </>
              ) : (
                <span className="text-[11px] text-amber-400 font-medium">Degraded</span>
              )}
            </div>
          </div>
        </>
      ) : (
        <div className="space-y-2">
          {[1, 2].map(i => (
            <div key={i} className="h-10 skeleton rounded-lg" />
          ))}
        </div>
      )}
    </Card>
  )
}
