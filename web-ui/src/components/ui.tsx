// Shared UI primitives – Card, SectionHeader, IconButton, Chip, StatusIcon
import { cn } from '../utils'
import type { RunState, ToolStatus } from '../types'
import {
  CheckCircle2, XCircle, Clock, AlertTriangle,
  Loader2, Hand, Ban
} from 'lucide-react'

// ─── Card ─────────────────────────────────────────────────────────
interface CardProps {
  children: React.ReactNode
  className?: string
  hoverable?: boolean
  raised?: boolean
  as?: 'div' | 'button' | 'article'
  onClick?: () => void
}
export function Card({ children, className, hoverable, raised, as: As = 'div', onClick }: CardProps) {
  return (
    <As
      onClick={onClick}
      className={cn(
        raised ? 'card-raised' : 'card',
        hoverable && 'card-hover cursor-pointer',
        className
      )}
    >
      {children}
    </As>
  )
}

// ─── SectionHeader ────────────────────────────────────────────────
interface SectionHeaderProps {
  icon?: React.ReactNode
  label: string
  count?: number | string
  action?: React.ReactNode
  className?: string
}
export function SectionHeader({ icon, label, count, action, className }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-center gap-2 mb-4', className)}>
      {icon && <span className="text-[var(--text-faint)]">{icon}</span>}
      <span className="text-micro text-[var(--text-faint)]">{label}</span>
      {count !== undefined && (
        <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-[var(--surface-2)] text-[var(--text-faint)] border border-[var(--border)]">
          {count}
        </span>
      )}
      {action && <div className="ml-auto">{action}</div>}
    </div>
  )
}

// ─── IconButton ───────────────────────────────────────────────────
interface IconButtonProps {
  onClick?: () => void
  title: string
  children: React.ReactNode
  className?: string
  spinning?: boolean
  'aria-label'?: string
}
export function IconButton({ onClick, title, children, className, spinning, 'aria-label': ariaLabel }: IconButtonProps) {
  return (
    <button
      onClick={onClick}
      title={title}
      aria-label={ariaLabel ?? title}
      className={cn(
        'flex items-center justify-center h-7 w-7 rounded-md text-[var(--text-faint)]',
        'hover:text-[var(--text-muted)] hover:bg-[var(--surface-2)]',
        'transition-colors focus-ring',
        spinning && 'pointer-events-none',
        className
      )}
    >
      <span className={cn(spinning && 'spin')}>{children}</span>
    </button>
  )
}

// ─── Chip (prompt quick-action) ───────────────────────────────────
interface ChipProps {
  icon: React.ReactNode
  label: string
  iconColor?: string
  onClick: () => void
  disabled?: boolean
}
export function Chip({ icon, label, iconColor, onClick, disabled }: ChipProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium',
        'bg-[var(--surface)] border border-[var(--border)]',
        'text-[var(--text-muted)] hover:text-[var(--text)]',
        'hover:border-[var(--border-strong)] hover:bg-[var(--surface-hover)]',
        'transition-all duration-150 focus-ring',
        disabled && 'opacity-40 cursor-not-allowed pointer-events-none'
      )}
    >
      <span className={cn('shrink-0', iconColor)}>{icon}</span>
      {label}
    </button>
  )
}

// ─── StatusIcon ───────────────────────────────────────────────────
const runStateIconMap: Record<RunState, { icon: React.ComponentType<{ className?: string }>, color: string }> = {
  completed:        { icon: CheckCircle2, color: 'text-emerald-400' },
  failed:           { icon: XCircle,      color: 'text-red-400' },
  cancelled:        { icon: Ban,          color: 'text-slate-500' },
  running:          { icon: Loader2,      color: 'text-cyan-400' },
  awaiting_approval:{ icon: Hand,         color: 'text-violet-400' },
  pending:          { icon: Clock,        color: 'text-slate-500' },
}

interface StatusIconProps {
  state: RunState
  className?: string
}
export function RunStatusIcon({ state, className }: StatusIconProps) {
  const { icon: Icon, color } = runStateIconMap[state] ?? { icon: Clock, color: 'text-slate-500' }
  const isSpinning = state === 'running'
  return (
    <Icon className={cn('h-3.5 w-3.5 shrink-0', color, isSpinning && 'spin', className)} />
  )
}

// ─── ToolStatusIcon ───────────────────────────────────────────────
export function ToolStatusIcon({ status, className }: { status: ToolStatus; className?: string }) {
  if (status === 'ok') return <CheckCircle2 className={cn('h-3.5 w-3.5 text-emerald-400', className)} />
  if (status === 'rejected') return <AlertTriangle className={cn('h-3.5 w-3.5 text-amber-400', className)} />
  if (status === 'blocked') return <Ban className={cn('h-3.5 w-3.5 text-red-400', className)} />
  if (status === 'timeout') return <Clock className={cn('h-3.5 w-3.5 text-orange-400', className)} />
  if (status === 'cancelled') return <XCircle className={cn('h-3.5 w-3.5 text-slate-500', className)} />
  return <XCircle className={cn('h-3.5 w-3.5 text-red-400', className)} />
}

// ─── Relative time helper ─────────────────────────────────────────
export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60)       return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60)       return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24)       return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}
