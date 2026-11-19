import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  CatalogPreset,
  LogLine,
  RunListItem,
  RunState,
  RunSummary,
  RunnerStatus,
  StartRunPayload,
  TestCaseState,
  TestStatus,
} from '../types/run'

interface UseRunStreamResult {
  run: RunState | null
  runs: RunListItem[]
  presets: CatalogPreset[]
  catalogCases: TestCaseState[]
  catalogCasesLoading: boolean
  runner: RunnerStatus
  connected: boolean
  loading: boolean
  error: string | null
  runBatchSeq: number
  selectRun: (runId: string) => Promise<void>
  startPresetRun: (payload: StartRunPayload) => Promise<void>
  runSingleCase: (tc: TestCaseState) => Promise<void>
  retryFailedRun: (runId: string) => Promise<void>
  resumeRun: (runId: string) => Promise<void>
  stopActiveRun: () => Promise<void>
  resetView: () => void
  deleteRuns: (runIds: string[]) => Promise<void>
  refreshCatalogCases: () => Promise<void>
}

export function useRunStream(): UseRunStreamResult {
  const [run, setRun] = useState<RunState | null>(null)
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [presets, setPresets] = useState<CatalogPreset[]>([])
  const [catalogCases, setCatalogCases] = useState<TestCaseState[]>([])
  const [catalogCasesLoading, setCatalogCasesLoading] = useState(true)
  const [runner, setRunner] = useState<RunnerStatus>({ is_running: false, is_admin: false })
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [runBatchSeq, setRunBatchSeq] = useState(0)

  const selectedRunIdRef = useRef<string | null>(null)
  const resetViewRef = useRef(true)
  const pendingLogsRef = useRef<Array<{ runId: string; log: LogLine }>>([])
  const rafRef = useRef<number | null>(null)

  const refreshRunsList = useCallback(async () => {
    try {
      const res = await fetch('/api/runs')
      if (!res.ok) return
      const data = await res.json()
      setRuns(data.runs ?? [])
      if (data.runner) {
        setRunner(() => {
          // Do not re-enable running state if we already received run_finish for that run
          if (data.runner.is_running && selectedRunIdRef.current === data.runner.active_run_id) {
            const matched = (data.runs ?? []).find((r: RunListItem) => r.run_id === data.runner.active_run_id)
            if (matched && matched.status !== 'running') {
              return { ...data.runner, is_running: false, active_run_id: null }
            }
          }
          return data.runner
        })
      }
    } catch {
      // ignore transient network errors
    }
  }, [])

  const loadCatalog = useCallback(async () => {
    try {
      const res = await fetch('/api/catalog')
      if (!res.ok) return
      const data = await res.json()
      setPresets(data.presets ?? [])
      if (data.runner) setRunner(data.runner)
    } catch {
      // ignore
    }
  }, [])

  const loadCatalogCases = useCallback(async (refresh = false) => {
    setCatalogCasesLoading(true)
    try {
      const url = refresh ? '/api/catalog/cases?refresh=true' : '/api/catalog/cases'
      const res = await fetch(url)
      if (!res.ok) return
      const data = await res.json()
      setCatalogCases(data.cases ?? [])
    } catch {
      // ignore
    } finally {
      setCatalogCasesLoading(false)
    }
  }, [])

  const refreshCatalogCases = useCallback(async () => {
    await loadCatalogCases(true)
  }, [loadCatalogCases])

  const selectRun = useCallback(async (runId: string) => {
    resetViewRef.current = false
    selectedRunIdRef.current = runId
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(runId)}`)
      if (!res.ok) throw new Error('실행 이력을 불러오지 못했습니다.')
      const data = await res.json()
      setRun(data.run)
      if (data.runner) setRunner(data.runner)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '알 수 없는 오류')
    }
  }, [])

  const flushLogs = useCallback(() => {
    rafRef.current = null
    const batch = pendingLogsRef.current.splice(0)
    if (batch.length === 0) return

    setRun((prev) => {
      if (!prev) return prev
      const relevant = batch.filter((b) => b.runId === prev.run_id)
      if (relevant.length === 0) return prev

      const byNode = new Map<string, LogLine[]>()
      const sessionExtras: LogLine[] = []
      for (const item of relevant) {
        if (item.log.nodeid) {
          const list = byNode.get(item.log.nodeid) ?? []
          list.push(item.log)
          byNode.set(item.log.nodeid, list)
        } else {
          sessionExtras.push(item.log)
        }
      }

      const nextCases =
        byNode.size > 0
          ? prev.cases.map((c) => {
              const added = byNode.get(c.nodeid)
              return added ? { ...c, logs: [...c.logs, ...added] } : c
            })
          : prev.cases

      return {
        ...prev,
        cases: nextCases,
        session_logs: sessionExtras.length > 0 ? [...prev.session_logs, ...sessionExtras] : prev.session_logs,
      }
    })
  }, [])

  useEffect(() => {
    let cancelled = false

    async function init() {
      void loadCatalogCases(false)
      await Promise.all([loadCatalog(), refreshRunsList()])
      try {
        const res = await fetch('/api/runs/latest')
        if (res.ok && !cancelled) {
          const data = await res.json()
          if (data.run && data.run.status === 'running' && !selectedRunIdRef.current) {
            resetViewRef.current = false
            selectedRunIdRef.current = data.run.run_id
            setRun(data.run)
          }
          if (data.runner) setRunner(data.runner)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    init()

    const es = new EventSource('/api/stream')

    es.onopen = () => {
      setConnected(true)
      setError(null)
    }

    es.onerror = () => {
      setConnected(false)
    }

    es.addEventListener('snapshot', (ev) => {
      const snap: RunState = JSON.parse((ev as MessageEvent).data)
      if (resetViewRef.current && snap.status !== 'running') {
        return
      }
      if (!selectedRunIdRef.current || selectedRunIdRef.current === snap.run_id) {
        resetViewRef.current = false
        selectedRunIdRef.current = snap.run_id
        setRun(snap)
      }
    })

    es.addEventListener('run_start', (ev) => {
      const nextRun: RunState = JSON.parse((ev as MessageEvent).data)
      resetViewRef.current = false
      selectedRunIdRef.current = nextRun.run_id
      pendingLogsRef.current = []
      setRunBatchSeq((n) => n + 1)
      setRun(nextRun)
      setRunner((prev) => ({ ...prev, is_running: true, active_run_id: nextRun.run_id }))
      refreshRunsList()
    })

    es.addEventListener('collection_ready', (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as {
        run_id: string
        cases: TestCaseState[]
        summary: RunSummary
      }
      setRun((prev) => {
        if (!prev || prev.run_id !== data.run_id) return prev
        return { ...prev, cases: data.cases, summary: data.summary }
      })
    })

    es.addEventListener('case_start', (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as {
        run_id: string
        nodeid: string
        started_at: string
        summary: RunSummary
      }
      setRun((prev) => {
        if (!prev || prev.run_id !== data.run_id) return prev
        return {
          ...prev,
          active_nodeid: data.nodeid,
          summary: data.summary,
          cases: prev.cases.map((c) =>
            c.nodeid === data.nodeid ? { ...c, status: 'running', started_at: data.started_at } : c,
          ),
        }
      })
    })

    es.addEventListener('log', (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as { run_id: string; log: LogLine }
      pendingLogsRef.current.push({ runId: data.run_id, log: data.log })
      if (rafRef.current === null) {
        rafRef.current = window.requestAnimationFrame(flushLogs)
      }
    })

    es.addEventListener('case_finish', (ev) => {
      // Flush any buffered logs immediately before finalizing the case
      if (rafRef.current !== null) {
        window.cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
      flushLogs()

      const data = JSON.parse((ev as MessageEvent).data) as {
        run_id: string
        nodeid: string
        status: TestStatus
        duration: number | null
        finished_at: string
        summary: string
        error_message: string
        run_summary: RunSummary
      }

      setRun((prev) => {
        if (!prev || prev.run_id !== data.run_id) return prev
        return {
          ...prev,
          active_nodeid: prev.active_nodeid === data.nodeid ? null : prev.active_nodeid,
          summary: data.run_summary,
          cases: prev.cases.map((c) =>
            c.nodeid === data.nodeid
              ? {
                  ...c,
                  status: data.status,
                  duration: data.duration,
                  finished_at: data.finished_at,
                  summary: data.summary,
                  error_message: data.error_message,
                }
              : c,
          ),
        }
      })
    })

    es.addEventListener('runner_status', (ev) => {
      const status = JSON.parse((ev as MessageEvent).data) as RunnerStatus
      setRunner(status)
    })

    es.addEventListener('runs_cleared', () => {
      selectedRunIdRef.current = null
      pendingLogsRef.current = []
      setRun(null)
      setRuns([])
    })

    es.addEventListener('runs_deleted', (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as { deleted_ids?: string[] }
      const deletedSet = new Set(data.deleted_ids ?? [])
      if (selectedRunIdRef.current && deletedSet.has(selectedRunIdRef.current)) {
        selectedRunIdRef.current = null
        pendingLogsRef.current = []
        setRun(null)
      }
      refreshRunsList()
    })

    es.addEventListener('run_finish', (ev) => {
      const data = JSON.parse((ev as MessageEvent).data) as {
        run_id: string
        status: RunState['status']
        finished_at: string
        summary: RunSummary
      }
      setRun((prev) => {
        if (!prev || prev.run_id !== data.run_id) return prev
        return {
          ...prev,
          status: data.status,
          finished_at: data.finished_at,
          active_nodeid: null,
          summary: data.summary,
        }
      })
      setRunner((prev) => ({ ...prev, is_running: false, active_run_id: null }))
      refreshRunsList()
    })

    return () => {
      cancelled = true
      if (rafRef.current !== null) window.cancelAnimationFrame(rafRef.current)
      es.close()
    }
  }, [flushLogs, loadCatalog, loadCatalogCases, refreshRunsList])

  const startPresetRun = useCallback(
    async (payload: StartRunPayload) => {
      setError(null)
      resetViewRef.current = false
      const targetRunId = payload.run_id ?? run?.run_id ?? null
      const res = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: payload.target,
          markers: payload.markers ?? null,
          paths: payload.paths ?? [],
          nodeids: payload.nodeids ?? [],
          keyword: payload.keyword?.trim() || null,
          title: payload.title,
          run_id: targetRunId,
          accumulate: Boolean(targetRunId) && (payload.accumulate ?? true),
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const msg = body.detail || '테스트 실행 시작에 실패했습니다.'
        setError(msg)
        throw new Error(msg)
      }
      const started = await res.json()
      selectedRunIdRef.current = started.run_id
      refreshRunsList()
    },
    [refreshRunsList, run?.run_id],
  )

  const runSingleCase = useCallback(
    async (tc: TestCaseState) => {
      const title = tc.tc_id ? `${tc.tc_id} · ${tc.title}` : tc.title
      await startPresetRun({
        target: tc.domain || 'custom',
        nodeids: [tc.nodeid],
        title,
        run_id: run?.run_id ?? null,
        accumulate: Boolean(run?.run_id),
      })
    },
    [run?.run_id, startPresetRun],
  )

  const retryFailedRun = useCallback(
    async (runId: string) => {
      setError(null)
      resetViewRef.current = false
      const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/retry-failed`, {
        method: 'POST',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const msg = body.detail || '실패 항목 재실행 시작에 실패했습니다.'
        setError(msg)
        throw new Error(msg)
      }
      selectedRunIdRef.current = runId
      refreshRunsList()
    },
    [refreshRunsList],
  )

  const resumeRun = useCallback(
    async (runId: string) => {
      setError(null)
      resetViewRef.current = false
      const res = await fetch(`/api/runs/${encodeURIComponent(runId)}/resume`, {
        method: 'POST',
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        const msg = body.detail || '이어서 진행 시작에 실패했습니다.'
        setError(msg)
        throw new Error(msg)
      }
      selectedRunIdRef.current = runId
      refreshRunsList()
    },
    [refreshRunsList],
  )

  const stopActiveRun = useCallback(async () => {
    const id = runner.active_run_id || run?.run_id
    if (!id) return
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(id)}/stop`, { method: 'POST' })
      if (res.ok) {
        const body = await res.json().catch(() => null)
        if (body?.runner) {
          setRunner(body.runner)
        }
      }
    } catch {
      // ignore
    }
  }, [run?.run_id, runner.active_run_id])

  const resetView = useCallback(() => {
    resetViewRef.current = true
    selectedRunIdRef.current = null
    pendingLogsRef.current = []
    setError(null)
    setRun(null)
  }, [])

  const deleteRuns = useCallback(
    async (runIds: string[]) => {
      if (runIds.length === 0) return
      setError(null)
      try {
        const res = await fetch('/api/runs', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ run_ids: runIds }),
        })
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          setError(body.detail || '이력 삭제에 실패했습니다.')
          return
        }
        const body = await res.json()
        const deletedSet = new Set<string>(body.deleted_ids ?? runIds)
        setRuns(body.runs ?? [])
        if (selectedRunIdRef.current && deletedSet.has(selectedRunIdRef.current)) {
          selectedRunIdRef.current = null
          pendingLogsRef.current = []
          setRun(null)
        }
      } catch {
        setError('이력 삭제 요청 중 오류가 발생했습니다.')
      }
    },
    [],
  )

  return {
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
  }
}
