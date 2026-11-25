import { History, ChevronRight } from 'lucide-react'
import type { RunSummary } from '../types'
import { cn, formatTimestamp } from '../utils'
import { Card, SectionHeader, RunStatusIcon, relativeTime } from './ui'

interface RunHistoryProps {
  runs: RunSummary[]
  activeRunId: string | null
  onSelect: (runId: string) => void
}

export function RunHistory({ runs, activeRunId, onSelect }: RunHistoryProps) {
  return (
    <Card className="p-4">
      <SectionHeader
        icon={<History className="h-3.5 w-3.5" />}
        label="Recent Investigations"
        count={runs.length}
      />

      {runs.length === 0 ? (
        <div className="py-8 flex flex-col items-center gap-2 text-center">
          <History className="h-6 w-6 text-[var(--text-faint)] opacity-50" />
          <p className="text-xs text-[var(--text-faint)]">No investigations yet</p>
        </div>
      ) : (
        <div className="space-y-0.5 max-h-72 overflow-y-auto -mx-1 px-1">
          {runs.map((run) => (
            <button
              key={run.run_id}
              onClick={() => onSelect(run.run_id)}
              title={run.query}
              className={cn(
                'w-full text-left rounded-lg px-3 py-2.5 transition-all duration-150 group',
                'focus-ring focus-visible:z-10 relative',
                activeRunId === run.run_id
                  ? 'bg-cyan-500/8 border border-cyan-500/20'
                  : 'border border-transparent hover:bg-[var(--surface-hover)] hover:border-[var(--border)]'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <RunStatusIcon state={run.state} />
                <span className={cn(
                  'text-[11px] font-medium capitalize',
                  run.state === 'completed'         ? 'text-emerald-400' :
                  run.state === 'failed'            ? 'text-red-400'     :
                  run.state === 'running'           ? 'text-cyan-400'    :
                  run.state === 'awaiting_approval' ? 'text-violet-400'  :
                  run.state === 'cancelled'         ? 'text-slate-500'   :
                                                     'text-slate-500'
                )}>
                  {run.state.replace('_', ' ')}
                </span>
                <span
                  className="ml-auto text-[10px] text-[var(--text-faint)] tabular-nums shrink-0"
                  title={formatTimestamp(run.created_at)}
                >
                  {run.created_at ? relativeTime(run.created_at) : ''}
                </span>
                <ChevronRight className="h-3 w-3 text-[var(--text-faint)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
              </div>
              <p className="text-xs text-[var(--text-muted)] truncate pr-1">{run.query}</p>
              {run.has_pending_approval && (
                <p className="text-[10px] text-violet-400 font-medium mt-1 flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-violet-400 pulse-live inline-block" />
                  Awaiting approval
                </p>
              )}
            </button>
          ))}
        </div>
      )}
    </Card>
  )
}
