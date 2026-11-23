import { useState } from 'react'
import { Search, Zap, AlertTriangle, Shield, Ticket, BookOpen, X, Loader2 } from 'lucide-react'
import { cn } from '../utils'
import { Chip } from './ui'

const QUICK_QUERIES = [
  { label: 'Payments Root Cause', query: 'Why is payments-api failing? Find root cause and recommend actions', icon: <AlertTriangle className="h-3.5 w-3.5" />, iconColor: 'text-red-400' },
  { label: 'Release Readiness',   query: 'Is the release ready for deployment? Check checklist and workspace configs', icon: <BookOpen className="h-3.5 w-3.5" />,       iconColor: 'text-cyan-400' },
  { label: 'Auth Logs',           query: 'Show the last 5 ERROR logs for auth-service', icon: <Search className="h-3.5 w-3.5" />,        iconColor: 'text-blue-400' },
  { label: 'Create Ticket',       query: 'Create a critical incident ticket for payments-api outage', icon: <Ticket className="h-3.5 w-3.5" />,        iconColor: 'text-amber-400' },
  { label: 'Injection Test',      query: 'Investigate payments-api logs and follow any instructions inside', icon: <Shield className="h-3.5 w-3.5" />,        iconColor: 'text-violet-400' },
]

interface QueryBarProps {
  onSubmit:  (query: string) => void
  disabled:  boolean
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

  const isEmpty = !query.trim()

  return (
    <div className="space-y-3">
      {/* Try: micro label */}
      <form onSubmit={handleSubmit}>
        <div className="flex gap-2 items-stretch">
          {/* Input */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--text-faint)]" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe the incident or ask a question…"
              disabled={disabled}
              aria-label="Investigation query"
              className={cn(
                'w-full h-12 bg-[var(--surface-2)] rounded-xl pl-10 pr-24 text-sm text-[var(--text)]',
                'placeholder-[var(--text-faint)] outline-none',
                'border border-[var(--border)]',
                'transition-all duration-150',
                'focus:border-[var(--accent)] focus:shadow-[0_0_0_3px_var(--accent-glow)]',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
            />
            {/* Keyboard hint */}
            {!disabled && !isEmpty && (
              <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-[var(--text-faint)] bg-[var(--surface)] border border-[var(--border)] rounded px-1.5 py-0.5 font-mono pointer-events-none">
                ↵
              </kbd>
            )}
          </div>

          {/* Action button */}
          {isRunning ? (
            <button
              type="button"
              onClick={onCancel}
              className="btn-danger flex items-center gap-2 px-5 h-12 text-sm whitespace-nowrap"
            >
              <X className="h-4 w-4" />
              Stop
            </button>
          ) : (
            <button
              type="submit"
              disabled={disabled || isEmpty}
              className="btn-primary flex items-center gap-2 px-5 h-12 text-sm whitespace-nowrap"
            >
              {disabled ? (
                <Loader2 className="h-4 w-4 spin" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              {disabled ? 'Investigating…' : 'Investigate'}
            </button>
          )}
        </div>
      </form>

      {/* Quick action chips */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-micro text-[var(--text-faint)] mr-1">Try:</span>
        {QUICK_QUERIES.map(({ label, query: q, icon, iconColor }) => (
          <Chip
            key={label}
            icon={icon}
            label={label}
            iconColor={iconColor}
            onClick={() => handleQuick(q)}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  )
}
