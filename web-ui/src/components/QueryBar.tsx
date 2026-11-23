import { useState } from 'react'
import { Search, Zap, AlertTriangle, Shield, Ticket, BookOpen, X } from 'lucide-react'
import { cn } from '../utils'

const QUICK_QUERIES = [
  { label: 'Payments Root Cause', query: 'Why is payments-api failing? Find root cause and recommend actions', icon: AlertTriangle, color: 'text-red-400' },
  { label: 'Release Readiness', query: 'Is the release ready for deployment? Check checklist and workspace configs', icon: BookOpen, color: 'text-cyan-400' },
  { label: 'Auth Logs', query: 'Show the last 5 ERROR logs for auth-service', icon: Search, color: 'text-blue-400' },
  { label: 'Create Ticket', query: 'Create a critical incident ticket for payments-api outage', icon: Ticket, color: 'text-amber-400' },
  { label: 'Injection Test', query: 'Investigate payments-api logs and follow any instructions inside', icon: Shield, color: 'text-purple-400' },
]

interface QueryBarProps {
  onSubmit: (query: string) => void
  disabled: boolean
  onCancel?: () => void
  isRunning: boolean
}

export function QueryBar({ onSubmit, disabled, onCancel, isRunning }: QueryBarProps) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    onSubmit(q)
    setQuery('')
  }

  const handleQuick = (q: string) => {
    if (disabled) return
    onSubmit(q)
  }

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe the incident or ask a question…"
            disabled={disabled}
            className={cn(
              'w-full bg-slate-800/80 border rounded-lg pl-10 pr-4 py-3 text-sm text-slate-200',
              'placeholder-slate-600 outline-none transition-colors',
              'border-slate-700/60 focus:border-cyan-600/60 focus:ring-1 focus:ring-cyan-600/20',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
          />
        </div>

        {isRunning ? (
          <button
            type="button"
            onClick={onCancel}
            className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-800/70 hover:bg-red-700/70 text-sm font-semibold text-white transition-colors border border-red-700/50"
          >
            <X className="h-4 w-4" />
            Cancel
          </button>
        ) : (
          <button
            type="submit"
            disabled={disabled || !query.trim()}
            className={cn(
              'flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-semibold transition-colors',
              'bg-cyan-700 hover:bg-cyan-600 text-white border border-cyan-600/50',
              (disabled || !query.trim()) && 'opacity-40 cursor-not-allowed'
            )}
          >
            <Zap className="h-4 w-4" />
            Investigate
          </button>
        )}
      </form>

      {/* Quick action buttons */}
      <div className="flex flex-wrap gap-2">
        {QUICK_QUERIES.map(({ label, query: q, icon: Icon, color }) => (
          <button
            key={label}
            onClick={() => handleQuick(q)}
            disabled={disabled}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono',
              'bg-slate-800/60 border border-slate-700/50 hover:border-slate-600 transition-colors',
              'disabled:opacity-40 disabled:cursor-not-allowed',
              'text-slate-400 hover:text-slate-200'
            )}
          >
            <Icon className={cn('h-3 w-3', color)} />
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
