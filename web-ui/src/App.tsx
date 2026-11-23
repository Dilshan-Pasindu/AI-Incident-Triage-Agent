import { useState, useCallback, useEffect, useRef } from 'react'
import { Activity, BarChart2, Terminal, List } from 'lucide-react'
import type { AgentEvent, RunSummary } from './types'
import { createRun, listRuns, cancelRun, getBenchmarks, getTraces } from './api'
import { useRunStream } from './hooks/useRunStream'
import { useHealth } from './hooks/useHealth'
import { QueryBar } from './components/QueryBar'
import { EventTimeline } from './components/EventTimeline'
import { HealthPanel } from './components/HealthPanel'
import { RunHistory } from './components/RunHistory'
import { cn, runStateColor, runStateDot } from './utils'

type Tab = 'investigate' | 'history' | 'benchmarks' | 'traces'

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('investigate')
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [benchmarks, setBenchmarks] = useState<string | null>(null)
  const [traces, setTraces] = useState<Record<string, unknown>[]>([])
  const timelineRef = useRef<HTMLDivElement>(null)

  const { health, error: healthError, refresh: refreshHealth } = useHealth()

  // SSE stream for the active run
  const handleEvent = useCallback((ev: AgentEvent) => {
    // Auto-refresh run list on run_stopped / final_answer
    if (ev.event_type === 'run_stopped' || ev.event_type === 'final_answer') {
      listRuns().then(setRuns).catch(() => {})
    }
    // Auto-scroll timeline
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

  // Load run list on mount and tab switch
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
    try {
      await cancelRun(activeRunId)
    } catch {
      // ignore
    }
  }

  const activeRun = runs.find((r) => r.run_id === activeRunId)
  const isRunning = activeRun?.state === 'running' || activeRun?.state === 'awaiting_approval' || submitting

  const TABS = [
    { id: 'investigate' as Tab, label: 'Investigate', icon: Terminal },
    { id: 'history' as Tab, label: 'History', icon: List },
    { id: 'benchmarks' as Tab, label: 'Benchmarks', icon: BarChart2 },
    { id: 'traces' as Tab, label: 'Traces', icon: Activity },
  ]

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Top Nav */}
      <header className="border-b border-slate-800/60 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-4">
          <div className="flex items-center gap-3">
            <img
              src="/logo.png"
              alt="Incident Triage Agent Logo"
              className="h-8 w-8 object-contain rounded-md border border-cyan-500/30 bg-slate-900 shadow-sm shadow-cyan-500/20"
            />
            <div>
              <h1 className="text-sm font-bold text-cyan-400 text-glow-cyan leading-none">Incident Triage Agent</h1>
              <p className="text-xs text-slate-500 leading-none mt-1">MCP-Powered Autonomous Investigation</p>
            </div>
          </div>

          {/* Tabs */}
          <nav className="flex gap-1 ml-6">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono transition-colors',
                  activeTab === id
                    ? 'bg-cyan-900/30 text-cyan-300 border border-cyan-700/40'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </nav>

          {/* Health indicator */}
          <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
            <span className={cn(
              'h-2 w-2 rounded-full',
              healthError ? 'bg-red-400' : health ? 'bg-emerald-400 animate-pulse-slow' : 'bg-slate-600'
            )} />
            {healthError ? 'Backend offline' : health ? `${health.tools_count} tools` : 'Connecting…'}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {activeTab === 'investigate' && (
          <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6">
            {/* Sidebar */}
            <div className="space-y-4">
              <HealthPanel health={health} error={healthError} onRefresh={refreshHealth} />
              <RunHistory
                runs={runs}
                activeRunId={activeRunId}
                onSelect={(id) => {
                  closeStream()
                  setActiveRunId(id)
                }}
              />
            </div>

            {/* Main Panel */}
            <div className="flex flex-col gap-4">
              {/* Query Bar */}
              <div className="rounded-lg border border-slate-700/50 bg-slate-900/50 p-4">
                <QueryBar
                  onSubmit={handleSubmit}
                  disabled={submitting}
                  onCancel={handleCancel}
                  isRunning={isRunning}
                />
                {errorMsg && (
                  <p className="mt-2 text-xs text-red-400 bg-red-900/20 border border-red-700/30 rounded px-3 py-2">
                    {errorMsg}
                  </p>
                )}
              </div>

              {/* Run Status Bar */}
              {activeRun && (
                <div className="flex items-center gap-3 px-4 py-2 rounded-lg border border-slate-700/40 bg-slate-900/30 text-xs">
                  <span className={cn('h-2 w-2 rounded-full', runStateDot(activeRun.state))} />
                  <span className={cn('font-mono uppercase font-semibold', runStateColor(activeRun.state))}>
                    {activeRun.state.replace('_', ' ')}
                  </span>
                  <span className="text-slate-500 truncate">{activeRun.query}</span>
                  <span className="ml-auto text-slate-600 font-mono shrink-0">{activeRun.run_id.slice(-8)}</span>
                </div>
              )}

              {/* Event Timeline */}
              <div
                ref={timelineRef}
                className="flex-1 rounded-lg border border-slate-700/50 bg-slate-900/30 p-4 overflow-y-auto"
                style={{ minHeight: '400px', maxHeight: '640px' }}
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

        {activeTab === 'history' && (
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-400 font-mono">All Investigations</h2>
            {runs.length === 0 ? (
              <p className="text-slate-600 text-sm text-center py-12">No investigations yet. Start one in the Investigate tab.</p>
            ) : (
              runs.map((run) => (
                <div
                  key={run.run_id}
                  onClick={() => { setActiveRunId(run.run_id); setActiveTab('investigate') }}
                  className="cursor-pointer rounded-lg border border-slate-700/50 bg-slate-900/50 hover:bg-slate-800/50 p-4 transition-colors"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className={cn('h-2 w-2 rounded-full', runStateDot(run.state))} />
                    <span className={cn('text-xs font-mono font-semibold uppercase', runStateColor(run.state))}>
                      {run.state.replace('_', ' ')}
                    </span>
                    <span className="ml-auto text-xs text-slate-600 font-mono">{run.run_id.slice(-12)}</span>
                  </div>
                  <p className="text-sm text-slate-300 mb-1">{run.query}</p>
                  {run.result_preview && (
                    <p className="text-xs text-slate-500 truncate">{run.result_preview}</p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {run.tools_used.slice(0, 5).map((t) => (
                      <code key={t} className="text-xs bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">{t}</code>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'benchmarks' && (
          <div className="rounded-lg border border-slate-700/50 bg-slate-900/30 p-6">
            <h2 className="text-sm font-semibold text-slate-400 font-mono mb-4">Benchmark Evaluation Report</h2>
            {benchmarks ? (
              <pre className="text-xs text-slate-300 font-sans whitespace-pre-wrap leading-relaxed">
                {benchmarks}
              </pre>
            ) : (
              <p className="text-slate-600 text-sm animate-pulse">Loading benchmark results…</p>
            )}
          </div>
        )}

        {activeTab === 'traces' && (
          <div className="rounded-lg border border-slate-700/50 bg-slate-900/30 p-6">
            <h2 className="text-sm font-semibold text-slate-400 font-mono mb-4">
              Audit Traces ({traces.length} records)
            </h2>
            <div className="space-y-2 max-h-screen overflow-y-auto">
              {traces.length === 0 ? (
                <p className="text-slate-600 text-sm text-center py-12">No trace records yet. Run an investigation first.</p>
              ) : (
                traces.map((trace, i) => (
                  <div key={i} className="rounded border border-slate-700/40 bg-slate-800/30 px-3 py-2">
                    <div className="flex items-center gap-3 mb-1 text-xs text-slate-500">
                      <span className="font-mono text-cyan-500">{String(trace['tool'] ?? '')}</span>
                      <span className={cn(
                        'font-mono uppercase font-semibold',
                        trace['status'] === 'ok' ? 'text-emerald-400' :
                          trace['status'] === 'rejected' ? 'text-amber-400' : 'text-red-400'
                      )}>
                        {String(trace['status'] ?? '')}
                      </span>
                      <span className="ml-auto">{String(trace['ts'] ?? '').slice(11, 19)}</span>
                      <span className="text-slate-600 font-mono">{String(trace['run_id'] ?? '').slice(-12)}</span>
                    </div>
                    <pre className="text-xs text-slate-400 truncate font-mono">
                      {String(trace['output_preview'] ?? '').slice(0, 200)}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
