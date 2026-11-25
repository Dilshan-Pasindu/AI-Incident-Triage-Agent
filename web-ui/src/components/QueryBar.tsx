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
  selectedModel: string
  onModelChange: (model: string) => void
  liveProviderLabel?: string
}

export function QueryBar({
  onSubmit,
  disabled,
  onCancel,
  isRunning,
  selectedModel,
  onModelChange,
  liveProviderLabel,
}: QueryBarProps) {
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
      {/* Top bar: Mode & Model Selector */}
      <div className="flex items-center justify-between gap-2 pb-1 text-xs">
        <span className="text-[var(--text-muted)] flex items-center gap-1.5 font-medium">
          <Zap className="h-3.5 w-3.5 text-cyan-400" />
          Incident Investigation
        </span>

        {/* Model Selector Toggle */}
        <div className="flex items-center gap-1 p-0.5 bg-[var(--surface-2)] border border-[var(--border)] rounded-lg">
          <button
            type="button"
            onClick={() => onModelChange('default')}
            disabled={disabled || isRunning}
            title="Use configured Live LLM (OpenRouter / xAI Grok / Google Gemini via .env)"
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-150',
              selectedModel === 'default'
                ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm'
                : 'text-[var(--text-faint)] hover:text-[var(--text)]',
              (disabled || isRunning) && 'opacity-60 cursor-not-allowed'
            )}
          >
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                selectedModel === 'default' ? 'bg-cyan-400 pulse-live' : 'bg-slate-500'
              )}
            />
            {liveProviderLabel ? `Live LLM (${liveProviderLabel})` : 'Live LLM'}
          </button>

          <button
            type="button"
            onClick={() => onModelChange('mock')}
            disabled={disabled || isRunning}
            title="Use deterministic offline mock (zero API cost)"
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-150',
              selectedModel === 'mock'
                ? 'bg-violet-500/15 text-violet-300 border border-violet-500/30 shadow-sm'
                : 'text-[var(--text-faint)] hover:text-[var(--text)]',
              (disabled || isRunning) && 'opacity-60 cursor-not-allowed'
            )}
          >
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                selectedModel === 'mock' ? 'bg-violet-400' : 'bg-slate-500'
              )}
            />
            Offline Mock
          </button>
        </div>
      </div>

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
