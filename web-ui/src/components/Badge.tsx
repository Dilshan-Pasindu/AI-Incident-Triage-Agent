import { cn } from '../utils'

// ─── Badge ────────────────────────────────────────────────────────
interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'cyan' | 'green' | 'red' | 'amber' | 'orange' | 'slate' | 'violet'
  className?: string
  dot?: boolean
  pulseDot?: boolean
}

const badgeVariants: Record<string, string> = {
  default: 'bg-[var(--surface-2)] text-[var(--text-muted)] border-[var(--border)]',
  cyan:    'bg-cyan-500/10    text-cyan-300    border-cyan-500/25',
  green:   'bg-emerald-500/10 text-emerald-300 border-emerald-500/25',
  red:     'bg-red-500/10     text-red-300     border-red-500/25',
  amber:   'bg-amber-500/10   text-amber-300   border-amber-500/25',
  orange:  'bg-orange-500/10  text-orange-300  border-orange-500/25',
  slate:   'bg-slate-800/60   text-slate-400   border-[var(--border)]',
  violet:  'bg-violet-500/10  text-violet-300  border-violet-500/25',
}

const dotColors: Record<string, string> = {
  default: 'bg-slate-400',
  cyan:    'bg-cyan-400',
  green:   'bg-emerald-400',
  red:     'bg-red-400',
  amber:   'bg-amber-400',
  orange:  'bg-orange-400',
  slate:   'bg-slate-500',
  violet:  'bg-violet-400',
}

export function Badge({ children, variant = 'default', className, dot, pulseDot }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border',
        badgeVariants[variant],
        className
      )}
    >
      {(dot || pulseDot) && (
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full shrink-0',
            dotColors[variant],
            pulseDot && 'pulse-live'
          )}
        />
      )}
      {children}
    </span>
  )
}
