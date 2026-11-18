import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  CatalogPreset,
  LogLine,
  RunListItem,
  RunState,
  RunSummary,
  RunnerStatus,
  TestCaseState,
  TestStatus,
} from '../types/run'

interface UseRunStreamResult {
  run: RunState | null
  runs: RunListItem[]
  presets: CatalogPreset[]
  runner: RunnerStatus
  connected: boolean
  loading: boolean
  error: string | null
  selectRun: (runId: string) => Promise<void>
  startPresetRun: (preset: CatalogPreset, keyword?: string) => Promise<void>
  stopActiveRun: () => Promise<void>
  clearAllRuns: () => Promise<void>
}

export function useRunStream(): UseRunStreamResult {
  const [run, setRun] = useState<RunState | null>(null)
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [presets, setPresets] = useState<CatalogPreset[]>([])
  const [runner, setRunner] = useState<RunnerStatus>({ is_running: false, is_admin: false })
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const selectedRunIdRef = useRef<string | null>(null)
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

  const selectRun = useCallback(async (runId: string) => {
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
      await Promise.all([loadCatalog(), refreshRunsList()])
      try {
        const res = await fetch('/api/runs/latest')
        if (res.ok && !cancelled) {
          const data = await res.json()
          if (data.run) {
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
      if (!selectedRunIdRef.current || selectedRunIdRef.current === snap.run_id) {
        selectedRunIdRef.current = snap.run_id
        setRun(snap)
      }
    })

    es.addEventListener('run_start', (ev) => {
      const nextRun: RunState = JSON.parse((ev as MessageEvent).data)
      selectedRunIdRef.current = nextRun.run_id
      pendingLogsRef.current = []
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
  }, [flushLogs, loadCatalog, refreshRunsList])

  const startPresetRun = useCallback(
    async (preset: CatalogPreset, keyword?: string) => {
      setError(null)
      const res = await fetch('/api/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: preset.id,
          markers: preset.markers ?? null,
          paths: preset.paths ?? [],
          keyword: keyword?.trim() || null,
          title: preset.label,
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

  const clearAllRuns = useCallback(async () => {
    setError(null)
    try {
      const res = await fetch('/api/runs', { method: 'DELETE' })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(body.detail || '초기화에 실패했습니다.')
        return
      }
      selectedRunIdRef.current = null
      pendingLogsRef.current = []
      setRun(null)
      setRuns([])
    } catch {
      setError('초기화 요청 중 오류가 발생했습니다.')
    }
  }, [])

  return {
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
  }
}
