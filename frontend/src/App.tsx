import { useEffect, useMemo, useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { ExecutionStream } from './components/ExecutionStream'
import { SummaryStrip } from './components/SummaryStrip'
import { TestTreePanel } from './components/TestTreePanel'
import { TopBar } from './components/TopBar'
import { useAutoFocus } from './hooks/useAutoFocus'
import { useRunStream } from './hooks/useRunStream'
import { buildHierarchyTree } from './types/run'

export function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('psi_dashboard_theme')
    return saved === 'light' ? 'light' : 'dark'
  })
  const [statusFilter, setStatusFilter] = useState<'all' | 'failed' | 'running' | 'passed'>('all')

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') root.classList.add('dark')
    else root.classList.remove('dark')
    localStorage.setItem('psi_dashboard_theme', theme)
  }, [theme])

  const {
    run,
    runs,
    presets,
    runner,
    connected,
    loading,
    error,
    selectRun,
    startPresetRun,
    stopActiveRun,
    clearAllRuns,
  } = useRunStream()

  const domains = useMemo(() => buildHierarchyTree(run?.cases ?? []), [run?.cases])
  const flatCategories = useMemo(() => domains.flatMap((d) => d.categories), [domains])

  const {
    autoFollow,
    setAutoFollow,
    expandedCategories,
    expandedCases,
    toggleCategory,
    toggleCase,
    focusCase,
    expandAll,
    collapsePassed,
    registerCaseRef,
  } = useAutoFocus(run, flatCategories)

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      <TopBar
        run={run}
        runs={runs}
        presets={presets}
        runner={runner}
        connected={connected}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
        onSelectRun={selectRun}
        onStartRun={startPresetRun}
        onStopRun={stopActiveRun}
        onClearRuns={clearAllRuns}
      />

      <SummaryStrip run={run} />

      {error && (
        <div
          className="flex shrink-0 items-center gap-2 border-b px-4 py-2 text-[12px]"
          style={{
            backgroundColor: 'var(--status-fail-bg)',
            borderColor: 'var(--status-fail-border)',
            color: 'var(--status-fail)',
          }}
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-1 items-center justify-center text-[13px]" style={{ color: 'var(--text-muted)' }}>
          대시보드 상태 불러오는 중...
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <TestTreePanel
            domains={domains}
            activeNodeId={run?.active_nodeid}
            statusFilter={statusFilter}
            onChangeStatusFilter={setStatusFilter}
            onSelectCase={focusCase}
          />
          <ExecutionStream
            run={run}
            domains={domains}
            statusFilter={statusFilter}
            autoFollow={autoFollow}
            expandedCategories={expandedCategories}
            expandedCases={expandedCases}
            onToggleAutoFollow={setAutoFollow}
            onToggleCategory={toggleCategory}
            onToggleCase={toggleCase}
            onExpandAll={expandAll}
            onCollapsePassed={collapsePassed}
            registerCaseRef={registerCaseRef}
          />
        </div>
      )}
    </div>
  )
}

export default App
