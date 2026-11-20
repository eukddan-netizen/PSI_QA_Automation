import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { ExecutionStream } from './components/ExecutionStream'
import { SummaryStrip } from './components/SummaryStrip'
import { TestTreePanel } from './components/TestTreePanel'
import { TopBar } from './components/TopBar'
import { useAutoFocus } from './hooks/useAutoFocus'
import { useLiveNow } from './hooks/useLiveNow'
import { useRunNotifications } from './hooks/useRunNotifications'
import { useRunStream } from './hooks/useRunStream'
import { buildHierarchyTree, mergeCatalogWithRunCases, type TestCaseState } from './types/run'

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
    catalogCases,
    catalogCasesLoading,
    runner,
    connected,
    loading,
    error,
    runBatchSeq,
    selectRun,
    startPresetRun,
    runSingleCase,
    retryFailedRun,
    resumeRun,
    stopActiveRun,
    resetView,
    deleteRuns,
    refreshCatalogCases,
  } = useRunStream()

  const {
    permission: notificationPermission,
    enabled: notificationsEnabled,
    toggleNotifications,
    ensurePermission: ensureNotificationPermission,
  } = useRunNotifications(run, runBatchSeq)

  const isRunActive = runner.is_running || run?.status === 'running'
  const hasRunningCase = useMemo(
    () => (run?.cases ?? []).some((c) => c.status === 'running'),
    [run?.cases],
  )
  const nowMs = useLiveNow(hasRunningCase, 500)
  const runDomains = useMemo(
    () => buildHierarchyTree(run?.cases ?? [], isRunActive),
    [run?.cases, isRunActive],
  )
  const mergedSidebarCases = useMemo(
    () => mergeCatalogWithRunCases(catalogCases, run?.cases ?? []),
    [catalogCases, run?.cases],
  )
  const sidebarDomains = useMemo(
    () => buildHierarchyTree(mergedSidebarCases, isRunActive),
    [mergedSidebarCases, isRunActive],
  )
  const runCaseNodeIds = useMemo(
    () => new Set((run?.cases ?? []).map((c) => c.nodeid)),
    [run?.cases],
  )
  const flatCategories = useMemo(() => runDomains.flatMap((d) => d.categories), [runDomains])

  const handleRunSingleCase = useCallback(
    async (tc: TestCaseState) => {
      void ensureNotificationPermission()
      await runSingleCase(tc)
    },
    [ensureNotificationPermission, runSingleCase],
  )

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
  } = useAutoFocus(run, flatCategories, runBatchSeq)

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      <TopBar
        run={run}
        runs={runs}
        presets={presets}
        runner={runner}
        connected={connected}
        theme={theme}
        notificationPermission={notificationPermission}
        notificationsEnabled={notificationsEnabled}
        onToggleNotifications={toggleNotifications}
        onEnsureNotificationPermission={ensureNotificationPermission}
        onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
        onSelectRun={selectRun}
        onStartRun={startPresetRun}
        onResumeRun={resumeRun}
        onRetryFailed={retryFailedRun}
        onStopRun={stopActiveRun}
        onResetView={resetView}
        onDeleteRuns={deleteRuns}
      />

      <SummaryStrip run={run} historyCount={runs.length} nowMs={nowMs} />

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
            runId={run?.run_id}
            runStatus={run?.status}
            runBatchSeq={runBatchSeq}
            domains={sidebarDomains}
            runCaseNodeIds={runCaseNodeIds}
            activeNodeId={run?.active_nodeid}
            isRunning={runner.is_running}
            nowMs={nowMs}
            catalogLoading={catalogCasesLoading}
            statusFilter={statusFilter}
            onChangeStatusFilter={setStatusFilter}
            onSelectCase={focusCase}
            onRunSingleCase={handleRunSingleCase}
            onRefreshCatalog={() => void refreshCatalogCases()}
          />
          <ExecutionStream
            run={run}
            historyCount={runs.length}
            domains={runDomains}
            statusFilter={statusFilter}
            autoFollow={autoFollow}
            isRunning={runner.is_running}
            nowMs={nowMs}
            expandedCategories={expandedCategories}
            expandedCases={expandedCases}
            onToggleAutoFollow={setAutoFollow}
            onToggleCategory={toggleCategory}
            onToggleCase={toggleCase}
            onRunSingleCase={handleRunSingleCase}
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
