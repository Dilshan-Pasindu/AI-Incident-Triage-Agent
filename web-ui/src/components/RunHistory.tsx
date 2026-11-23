import { History, ChevronRight } from 'lucide-react'
import type { RunSummary } from '../types'
import { cn, formatTimestamp, runStateDot, runStateColor } from '../utils'

interface RunHistoryProps {
  runs: RunSummary[]
  activeRunId: string | null
  onSelect: (runId: string) => void
}

export function RunHistory({ runs, activeRunId, onSelect }: RunHistoryProps) {
  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <History className="h-4 w-4 text-slate-400" />
        <span className="text-sm font-semibold text-slate-300">Recent Investigations</span>
        <span className="ml-auto text-xs text-slate-600">{runs.length}</span>
      </div>

      {runs.length === 0 ? (
        <p className="text-xs text-slate-600 text-center py-4">No investigations yet</p>
      ) : (
        <div className="space-y-1 max-h-72 overflow-y-auto">
          {runs.map((run) => (
            <button
              key={run.run_id}
              onClick={() => onSelect(run.run_id)}
              className={cn(
                'w-full text-left rounded px-3 py-2 transition-colors group',
                activeRunId === run.run_id
                  ? 'bg-cyan-900/20 border border-cyan-700/40'
                  : 'hover:bg-slate-800/60 border border-transparent'
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={cn('h-2 w-2 rounded-full shrink-0', runStateDot(run.state))} />
                <span className={cn('text-xs font-mono', runStateColor(run.state))}>
                  {run.state.replace('_', ' ')}
                </span>
                <span className="ml-auto text-xs text-slate-600 shrink-0">
                  {run.created_at ? formatTimestamp(run.created_at) : ''}
                </span>
                <ChevronRight className="h-3 w-3 text-slate-600 group-hover:text-slate-400 transition-colors" />
              </div>
              <p className="text-xs text-slate-400 truncate pr-2">{run.query}</p>
              {run.has_pending_approval && (
                <p className="text-xs text-amber-400 mt-1 font-semibold">⏳ Awaiting Approval</p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
