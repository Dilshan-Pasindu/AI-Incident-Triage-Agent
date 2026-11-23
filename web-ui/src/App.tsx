import { useState, useCallback, useEffect, useRef } from 'react'
import { Activity, BarChart2, Terminal, List, Zap } from 'lucide-react'
import type { AgentEvent, RunSummary } from './types'
import { createRun, listRuns, cancelRun, getBenchmarks, getTraces } from './api'
import { useRunStream } from './hooks/useRunStream'
import { useHealth } from './hooks/useHealth'
import { QueryBar } from './components/QueryBar'
import { EventTimeline } from './components/EventTimeline'
import { HealthPanel } from './components/HealthPanel'
import { RunHistory } from './components/RunHistory'
import { Badge } from './components/Badge'
import { RunStatusIcon, relativeTime } from './components/ui'
import { cn, runStateColor, formatTimestamp, formatMs } from './utils'

type Tab = 'investigate' | 'history' | 'benchmarks' | 'traces'

export default function App() {
  const [activeTab, setActiveTab]       = useState<Tab>('investigate')
  const [activeRunId, setActiveRunId]   = useState<string | null>(null)
  const [runs, setRuns]                 = useState<RunSummary[]>([])
  const [submitting, setSubmitting]     = useState(false)
  const [errorMsg, setErrorMsg]         = useState<string | null>(null)
  const [benchmarks, setBenchmarks]     = useState<string | null>(null)
  const [traces, setTraces]             = useState<Record<string, unknown>[]>([])
  const timelineRef = useRef<HTMLDivElement>(null)

  const { health, error: healthError, refresh: refreshHealth } = useHealth()

  const handleEvent = useCallback((ev: AgentEvent) => {
    if (ev.event_type === 'run_stopped' || ev.event_type === 'final_answer') {
      listRuns().then(setRuns).catch(() => {})
    }
    setTimeout(() => {
      if (timelineRef.current) {
        timelineRef.current.scrollTop = timelineRef.current.scrollHeight
      }
    }, 50)
  }, [])

  const { events, close: closeStream } = useRunStream({
    runId: activeRunId,
    onEvent: handleEvent,
  })

  useEffect(() => {
    if (activeTab === 'history' || activeTab === 'investigate') {
      listRuns().then(setRuns).catch(() => {})
    }
    if (activeTab === 'benchmarks' && !benchmarks) {
      getBenchmarks().then((r) => setBenchmarks(r.content)).catch(() => {
        setBenchmarks('No benchmark report found. Run the eval suite first.')
      })
    }
    if (activeTab === 'traces') {
      getTraces().then(setTraces).catch(() => {})
    }
  }, [activeTab]) // eslint-disable-line

  const handleSubmit = async (query: string) => {
    setSubmitting(true)
    setErrorMsg(null)
    closeStream()
    setActiveRunId(null)
    try {
      const run = await createRun(query, 'mock')
      setActiveRunId(run.run_id)
      setRuns((prev) => [run, ...prev.filter((r) => r.run_id !== run.run_id)])
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : 'Failed to start investigation')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = async () => {
    if (!activeRunId) return
    try { await cancelRun(activeRunId) } catch { /* ignore */ }
  }

  const activeRun = runs.find((r) => r.run_id === activeRunId)
  const isRunning = activeRun?.state === 'running' || activeRun?.state === 'awaiting_approval' || submitting

  const allHealthy = !healthError && health &&
    health.mcp_servers.ops.health === 'healthy' &&
    health.mcp_servers.fs.health === 'healthy'

  const TABS = [
    { id: 'investigate' as Tab, label: 'Investigate', icon: Terminal },
    { id: 'history'     as Tab, label: 'History',     icon: List },
    { id: 'benchmarks'  as Tab, label: 'Benchmarks',  icon: BarChart2 },
    { id: 'traces'      as Tab, label: 'Traces',       icon: Activity },
  ]

  return (
    <div className="min-h-screen page-glow" style={{ background: 'var(--bg)', fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* ─── Header ───────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-20 border-b"
        style={{
          background: 'rgba(8, 13, 26, 0.85)',
          backdropFilter: 'blur(12px)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="max-w-content mx-auto px-6 h-14 flex items-center gap-6">
          {/* Logo + wordmark */}
          <div className="flex items-center gap-3 shrink-0">
            <img
              src="/logo.png"
              alt="Incident Triage Agent Logo"
              className="h-8 w-8 object-contain"
              style={{ filter: 'drop-shadow(0 0 10px rgba(34,211,238,0.4))' }}
            />
            <div>
              <h1 className="text-sm font-bold leading-none" style={{ color: 'var(--accent)', letterSpacing: '-0.01em' }}>
                Incident Triage Agent
              </h1>
              <p className="text-[11px] leading-none mt-1" style={{ color: 'var(--text-faint)' }}>
                MCP-Powered Autonomous Investigation
              </p>
            </div>
          </div>

          {/* Nav tabs */}
          <nav className="flex gap-1 ml-2" role="tablist">
            {TABS.map(({ id, label, icon: Icon }) => {
              const isActive = activeTab === id
              return (
                <button
                  key={id}
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => setActiveTab(id)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 focus-ring',
                    isActive
                      ? 'bg-[var(--surface-2)] border border-[var(--border-strong)] text-[var(--text)]'
                      : 'text-[var(--text-faint)] hover:text-[var(--text-muted)] hover:bg-[var(--surface)]'
                  )}
                >
                  <Icon className={cn('h-3.5 w-3.5', isActive && 'text-[var(--accent)]')} />
                  {label}
                </button>
              )
            })}
          </nav>

          {/* Health status cluster */}
          <div className="ml-auto flex items-center gap-2">
            <span
              className={cn(
                'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border',
                allHealthy
                  ? 'bg-emerald-500/8 border-emerald-500/20 text-emerald-400'
                  : healthError
                    ? 'bg-red-500/8 border-red-500/20 text-red-400'
                    : 'border-[var(--border)] text-[var(--text-faint)]'
              )}
              title={health?.tools.slice(0, 10).join(', ') ?? ''}
            >
              <span className={cn(
                'h-2 w-2 rounded-full',
                allHealthy  ? 'bg-emerald-400 pulse-live' :
                healthError ? 'bg-red-400'                :
                              'bg-slate-600'
              )} />
              <span className="font-medium tabular-nums">
                {healthError ? 'Backend offline' :
                 health     ? `${health.tools_count} tools` :
                              'Connecting…'}
              </span>
            </span>
          </div>
        </div>
      </header>

      {/* ─── Main ─────────────────────────────────────────────────── */}
      <main className="max-w-content mx-auto w-full px-6 py-6">

        {/* ── Investigate ─────────────────────────────────────────── */}
        {activeTab === 'investigate' && (
          <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-5">
            {/* Left rail */}
            <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start lg:max-h-[calc(100vh-5rem)] lg:overflow-y-auto">
              <HealthPanel health={health} error={healthError} onRefresh={refreshHealth} />
              <RunHistory
                runs={runs}
                activeRunId={activeRunId}
                onSelect={(id) => {
                  closeStream()
                  setActiveRunId(id)
                }}
              />
            </aside>

            {/* Main area */}
            <div className="flex flex-col gap-4">
              {/* Query section */}
              <div
                className="rounded-xl border p-4"
                style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
              >
                <QueryBar
                  onSubmit={handleSubmit}
                  disabled={submitting}
                  onCancel={handleCancel}
                  isRunning={isRunning}
                />
                {errorMsg && (
                  <p className="mt-3 text-xs text-red-400 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2">
                    {errorMsg}
                  </p>
                )}
              </div>

              {/* Run status bar */}
              {activeRun && (
                <div
                  className="flex items-center gap-3 px-4 py-2.5 rounded-xl border text-xs fade-slide-in"
                  style={{ background: 'var(--surface)', borderColor: 'var(--border)' }}
                >
                  <RunStatusIcon state={activeRun.state} />
                  <span className={cn('font-semibold capitalize', runStateColor(activeRun.state))}>
                    {activeRun.state.replace('_', ' ')}
                  </span>
                  <span className="text-[var(--text-faint)] truncate">{activeRun.query}</span>
                  <code className="ml-auto text-[var(--text-faint)] font-mono shrink-0 tabular-nums">
                    {activeRun.run_id.slice(-8)}
                  </code>
                </div>
              )}

              {/* Event timeline */}
              <div
                ref={timelineRef}
                className="rounded-xl border p-4 overflow-y-auto"
                style={{
                  background: 'var(--surface)',
                  borderColor: 'var(--border)',
                  minHeight: '420px',
                  maxHeight: '660px',
                }}
                aria-live="polite"
              >
                <EventTimeline
                  events={events}
                  onApprovalResolved={() => {
                    listRuns().then(setRuns).catch(() => {})
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* ── History ─────────────────────────────────────────────── */}
        {activeTab === 'history' && (
          <div>
            <div className="flex items-start gap-3 mb-6">
              <div>
                <h2 className="text-section-title text-[var(--text)]">All Investigations</h2>
                <p className="text-xs text-[var(--text-faint)] mt-0.5">{runs.length} records</p>
              </div>
            </div>

            {runs.length === 0 ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] py-20 text-center">
                <List className="h-8 w-8 text-[var(--text-faint)] mx-auto mb-3 opacity-40" />
                <p className="text-sm text-[var(--text-faint)]">No investigations yet. Start one in the Investigate tab.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {runs.map((run) => (
                  <div
                    key={run.run_id}
                    onClick={() => { setActiveRunId(run.run_id); setActiveTab('investigate') }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { setActiveRunId(run.run_id); setActiveTab('investigate') } }}
                    className="cursor-pointer rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] hover:border-[var(--border-strong)] p-4 transition-all focus-ring"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <RunStatusIcon state={run.state} />
                      <span className={cn('text-xs font-semibold capitalize', runStateColor(run.state))}>
                        {run.state.replace('_', ' ')}
                      </span>
                      {run.tools_used.length > 0 && (
                        <span className="text-[11px] text-[var(--text-faint)]">
                          via {run.tools_used.length} tool{run.tools_used.length > 1 ? 's' : ''}
                        </span>
                      )}
                      <code className="ml-auto text-[10px] text-[var(--text-faint)] font-mono tabular-nums">{run.run_id.slice(-12)}</code>
                      <span
                        className="text-[11px] text-[var(--text-faint)] tabular-nums"
                        title={run.created_at ? formatTimestamp(run.created_at) : ''}
                      >
                        {run.created_at ? relativeTime(run.created_at) : ''}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--text)] mb-1 leading-snug">{run.query}</p>
                    {run.result_preview && (
                      <p className="text-xs text-[var(--text-faint)] truncate mb-2">{run.result_preview}</p>
                    )}
                    {run.tools_used.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {run.tools_used.slice(0, 6).map((t) => (
                          <code key={t} className="text-[10px] bg-[var(--surface-2)] text-[var(--text-muted)] px-2 py-0.5 rounded font-mono border border-[var(--border)]">
                            {t}
                          </code>
                        ))}
                        {run.tools_used.length > 6 && (
                          <span className="text-[10px] text-[var(--text-faint)] px-1">+{run.tools_used.length - 6} more</span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Benchmarks ──────────────────────────────────────────── */}
        {activeTab === 'benchmarks' && (
          <div>
            <div className="mb-6">
              <h2 className="text-section-title text-[var(--text)]">Benchmark Evaluation Report</h2>
              <p className="text-xs text-[var(--text-faint)] mt-0.5">Automated evaluation results for the agent reasoning pipeline</p>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
              {benchmarks ? (
                <pre className="text-xs text-[var(--text-muted)] font-mono whitespace-pre-wrap leading-relaxed">
                  {benchmarks}
                </pre>
              ) : (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map(i => (
                    <div key={i} className={`h-4 skeleton rounded`} style={{ width: `${60 + (i * 7) % 40}%` }} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Traces ──────────────────────────────────────────────── */}
        {activeTab === 'traces' && (
          <div>
            <div className="mb-6">
              <h2 className="text-section-title text-[var(--text)]">Audit Traces</h2>
              <p className="text-xs text-[var(--text-faint)] mt-0.5 tabular-nums">{traces.length} records</p>
            </div>

            {traces.length === 0 ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] py-20 text-center">
                <Activity className="h-8 w-8 text-[var(--text-faint)] mx-auto mb-3 opacity-40" />
                <p className="text-sm text-[var(--text-faint)]">No trace records yet. Run an investigation first.</p>
              </div>
            ) : (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
                {/* Table header */}
                <div className="grid grid-cols-[1fr_80px_80px_1fr_90px] gap-4 px-4 py-2.5 border-b border-[var(--border)] bg-[var(--surface-2)] sticky top-14">
                  {['Tool', 'Status', 'Time', 'Output Preview', 'Run'].map(h => (
                    <span key={h} className="text-micro">{h}</span>
                  ))}
                </div>

                <div className="divide-y divide-[var(--border)] max-h-[70vh] overflow-y-auto">
                  {traces.map((trace, i) => {
                    const status = String(trace['status'] ?? '')
                    const isOk       = status === 'ok'
                    const isRejected = status === 'rejected'
                    return (
                      <div
                        key={i}
                        className="grid grid-cols-[1fr_80px_80px_1fr_90px] gap-4 px-4 py-3 hover:bg-[var(--surface-hover)] transition-colors"
                      >
                        <code className="text-xs font-mono text-cyan-400 truncate">{String(trace['tool'] ?? '')}</code>
                        <span>
                          <Badge
                            variant={isOk ? 'green' : isRejected ? 'amber' : 'red'}
                            className="text-[10px]"
                          >
                            {status}
                          </Badge>
                        </span>
                        <span className="text-xs text-[var(--text-faint)] font-mono tabular-nums">
                          {String(trace['ts'] ?? '').slice(11, 19)}
                        </span>
                        <pre className="text-xs text-[var(--text-muted)] font-mono truncate">
                          {String(trace['output_preview'] ?? '').slice(0, 100)}
                        </pre>
                        <code className="text-[10px] text-[var(--text-faint)] font-mono tabular-nums truncate">
                          {String(trace['run_id'] ?? '').slice(-8)}
                        </code>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
