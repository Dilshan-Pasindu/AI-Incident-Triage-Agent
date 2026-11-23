import { cn } from '../utils'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'cyan' | 'green' | 'red' | 'amber' | 'orange' | 'slate'
  className?: string
}

const variantMap: Record<string, string> = {
  default: 'bg-slate-800 text-slate-300 border-slate-700',
  cyan: 'bg-cyan-900/40 text-cyan-300 border-cyan-700/50',
  green: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50',
  red: 'bg-red-900/40 text-red-300 border-red-700/50',
  amber: 'bg-amber-900/40 text-amber-300 border-amber-700/50',
  orange: 'bg-orange-900/40 text-orange-300 border-orange-700/50',
  slate: 'bg-slate-800/60 text-slate-400 border-slate-700/50',
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono border',
        variantMap[variant],
        className
      )}
    >
      {children}
    </span>
  )
}
