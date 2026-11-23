import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { RunState, ToolStatus } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatMs(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function toolStatusColor(status: ToolStatus): string {
  switch (status) {
    case 'ok': return 'text-emerald-400'
    case 'rejected': return 'text-amber-400'
    case 'blocked': return 'text-red-400'
    case 'timeout': return 'text-orange-400'
    case 'invalid': return 'text-yellow-400'
    case 'error': return 'text-red-500'
    case 'cancelled': return 'text-slate-400'
    default: return 'text-slate-400'
  }
}

export function toolStatusBg(status: ToolStatus): string {
  switch (status) {
    case 'ok': return 'bg-emerald-900/30 border-emerald-700/40'
    case 'rejected': return 'bg-amber-900/30 border-amber-700/40'
    case 'blocked': return 'bg-red-900/30 border-red-700/40'
    case 'timeout': return 'bg-orange-900/30 border-orange-700/40'
    case 'invalid': return 'bg-yellow-900/30 border-yellow-700/40'
    case 'error': return 'bg-red-900/40 border-red-700/50'
    default: return 'bg-slate-800/40 border-slate-700/40'
  }
}

export function runStateColor(state: RunState): string {
  switch (state) {
    case 'running': return 'text-cyan-400'
    case 'awaiting_approval': return 'text-amber-400'
    case 'completed': return 'text-emerald-400'
    case 'failed': return 'text-red-400'
    case 'cancelled': return 'text-slate-400'
    case 'pending': return 'text-slate-400'
    default: return 'text-slate-400'
  }
}

export function runStateDot(state: RunState): string {
  switch (state) {
    case 'running': return 'bg-cyan-400 animate-pulse'
    case 'awaiting_approval': return 'bg-amber-400 animate-pulse'
    case 'completed': return 'bg-emerald-400'
    case 'failed': return 'bg-red-400'
    case 'cancelled': return 'bg-slate-500'
    default: return 'bg-slate-600'
  }
}
