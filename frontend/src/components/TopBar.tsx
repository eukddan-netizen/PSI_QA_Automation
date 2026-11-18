import { useEffect, useMemo, useRef, useState } from 'react'
import {
  FileSpreadsheet,
  FileText,
  Monitor,
  Moon,
  Play,
  RotateCcw,
  Shield,
  Square,
  StepForward,
  Sun,
} from 'lucide-react'
import type { CatalogPreset, RunListItem, RunState, RunnerStatus, StartRunPayload } from '../types/run'
import { RunHistorySelector } from './RunHistorySelector'
import { TargetSelector, buildRunPayload } from './TargetSelector'

interface TopBarProps {
  run: RunState | null
  runs: RunListItem[]
  presets: CatalogPreset[]
  runner: RunnerStatus
  connected: boolean
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  onSelectRun: (runId: string) => void
  onStartRun: (payload: StartRunPayload) => Promise<void>
  onResumeRun: (runId: string) => Promise<void>
  onStopRun: () => Promise<void>
  onResetView: () => void
  onDeleteRuns: (runIds: string[]) => Promise<void>
}

export function TopBar({
  run,
  runs,
  presets,
  runner,
  connected,
  theme,
  onToggleTheme,
  onSelectRun,
  onStartRun,
  onResumeRun,
  onStopRun,
  onResetView,
  onDeleteRuns,
}: TopBarProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const [useAllTarget, setUseAllTarget] = useState(false)
  const [launching, setLaunching] = useState(false)
  const [resuming, setResuming] = useState(false)
  const initializedRef = useRef(false)

  useEffect(() => {
    if (!initializedRef.current && presets.length > 0) {
      initializedRef.current = true
      const appChildIds = presets
        .filter((p) => p.domain === 'app_checks' && p.id !== 'app_all')
        .map((p) => p.id)
      setSelectedIds(new Set(appChildIds))
    }
  }, [presets])

  const runPayload = useMemo(
    () => buildRunPayload(presets, selectedIds, useAllTarget),
    [presets, selectedIds, useAllTarget],
  )
  const canExport = Boolean(run && run.cases.length > 0)
  const completedCount = run?.summary.completed ?? 0
  const totalCount = run?.summary.total ?? 0
  const pendingCount = run?.summary.pending ?? 0
  const canResume = Boolean(
    !runner.is_running &&
      run &&
      pendingCount > 0 &&
      (run.status === 'stopped' || run.status === 'failed'),
  )

  const handleLaunch = async () => {
    if (!runPayload || launching || resuming) return
    setLaunching(true)
    try {
      await onStartRun(runPayload)
    } finally {
      setLaunching(false)
    }
  }

  const handleResume = async () => {
    if (!run || !canResume || resuming || launching) return
    setResuming(true)
    try {
      await onResumeRun(run.run_id)
    } finally {
      setResuming(false)
    }
  }

  const handleDownload = (format: 'xlsx' | 'docx') => {
    if (!run) return
    const url = `/api/runs/${encodeURIComponent(run.run_id)}/report?format=${format}`
    const a = document.createElement('a')
    a.href = url
    a.download = ''
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <header
      className="flex h-13 shrink-0 items-center justify-between border-b px-4"
      style={{
        backgroundColor: 'var(--bg-header)',
        borderColor: 'var(--border-header)',
        color: 'var(--text-header)',
      }}
    >
      {/* Left: Brand & Live Connection & Run History */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-7 w-7 items-center justify-center rounded border"
            style={{
              backgroundColor: 'var(--bg-header-control)',
              borderColor: 'var(--border-header)',
              color: 'var(--text-header)',
            }}
          >
            <Monitor className="h-3.5 w-3.5" />
          </div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold tracking-tight" style={{ color: 'var(--text-header)' }}>
              PSI QA Monitor
            </div>
            <div className="flex items-center gap-1.5 text-[11px]" style={{ color: 'var(--text-header-muted)' }}>
              <span
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{
                  backgroundColor: connected ? '#34d399' : '#f87171',
                }}
              />
              <span>{connected ? 'SSE 실시간 연결' : '연결 대기중'}</span>
              <span>·</span>
              <span className="inline-flex items-center gap-0.5">
                <Shield className="h-2.5 w-2.5" />
                {runner.is_admin ? '관리자 권한' : '일반 권한'}
              </span>
            </div>
          </div>
        </div>

        <div className="h-5 w-px mx-1" style={{ backgroundColor: 'var(--border-header)' }} />

        {/* Run Selector & Reset */}
        {(runs.length > 0 || run !== null) && (
          <div className="flex items-center gap-1.5 min-w-0">
            {runs.length > 0 && (
              <RunHistorySelector
                currentRun={run}
                runs={runs}
                isRunning={runner.is_running}
                onSelectRun={onSelectRun}
                onDeleteRuns={onDeleteRuns}
              />
            )}

            <button
              type="button"
              disabled={runner.is_running || !run}
              onClick={onResetView}
              title="현재 화면을 테스트 전 초기 상태로 되돌립니다 (저장된 DB 이력은 유지됩니다)"
              className="inline-flex h-8 shrink-0 items-center gap-1 rounded border px-2.5 text-[11.5px] font-medium transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
              style={{
                backgroundColor: 'var(--bg-header-control)',
                borderColor: 'var(--border-header)',
                color: 'var(--text-header)',
              }}
            >
              <RotateCcw className="h-3 w-3" />
              <span>초기화</span>
            </button>
          </div>
        )}
      </div>

      {/* Right: Runner Controls + Theme + Government Report Export Buttons */}
      <div className="flex items-center gap-2">
        {/* Hierarchical Checkbox Target Launcher */}
        <div className="flex items-center gap-2">
          <TargetSelector
            presets={presets}
            disabled={runner.is_running}
            selectedIds={selectedIds}
            useAllTarget={useAllTarget}
            onChangeSelection={(nextIds, nextUseAll) => {
              setSelectedIds(nextIds)
              setUseAllTarget(nextUseAll)
            }}
          />

          {runner.is_running ? (
            <button
              type="button"
              onClick={onStopRun}
              className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded border px-3 text-[12px] font-medium transition-colors cursor-pointer"
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.18)',
                borderColor: 'rgba(248, 113, 113, 0.45)',
                color: '#fca5a5',
              }}
            >
              <Square className="h-3 w-3 fill-current" />
              <span>중단</span>
            </button>
          ) : (
            <>
              {canResume && (
                <button
                  type="button"
                  onClick={handleResume}
                  disabled={resuming || launching}
                  title={`중단/미완료된 대기 항목 ${pendingCount}건을 이어서 실행합니다`}
                  className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded border px-2.5 text-[12px] font-medium transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  style={{
                    backgroundColor: 'rgba(245, 158, 11, 0.16)',
                    borderColor: 'rgba(251, 191, 36, 0.45)',
                    color: '#fcd34d',
                  }}
                >
                  <StepForward className="h-3.5 w-3.5" />
                  <span>{resuming ? '재개중...' : `이어서 진행 (${pendingCount}건)`}</span>
                </button>
              )}
              <button
                type="button"
                onClick={handleLaunch}
                disabled={!runPayload || launching || resuming}
                className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded px-3 text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                style={{ backgroundColor: 'var(--accent-primary)' }}
              >
                <Play className="h-3 w-3 fill-current" />
                <span>{launching ? '시작중...' : '테스트 실행'}</span>
              </button>
            </>
          )}
        </div>

        <div className="h-5 w-px mx-0.5" style={{ backgroundColor: 'var(--border-header)' }} />

        {/* Export Snapshot Buttons */}
        <div
          className="flex items-center gap-1.5"
          title={
            canExport
              ? `현재 시점까지 완료된 테스트(${completedCount}/${totalCount}건) 기준 보고서 즉시 추출`
              : '수집된 테스트 결과가 있을 때 보고서를 추출할 수 있습니다'
          }
        >
          <button
            type="button"
            disabled={!canExport}
            onClick={() => handleDownload('xlsx')}
            className="inline-flex h-8 items-center gap-1.5 rounded border px-2.5 text-[12px] font-medium transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-header-control)',
              borderColor: 'var(--border-header)',
              color: 'var(--text-header)',
            }}
          >
            <FileSpreadsheet className="h-3.5 w-3.5" style={{ color: '#34d399' }} />
            <span>Excel</span>
          </button>

          <button
            type="button"
            disabled={!canExport}
            onClick={() => handleDownload('docx')}
            className="inline-flex h-8 items-center gap-1.5 rounded border px-2.5 text-[12px] font-medium transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-header-control)',
              borderColor: 'var(--border-header)',
              color: 'var(--text-header)',
            }}
          >
            <FileText className="h-3.5 w-3.5" style={{ color: '#60a5fa' }} />
            <span>Word</span>
          </button>
        </div>

        {/* Theme Toggle */}
        <button
          type="button"
          onClick={onToggleTheme}
          title={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
          className="flex h-8 w-8 items-center justify-center rounded border transition-opacity hover:opacity-85 cursor-pointer"
          style={{
            backgroundColor: 'var(--bg-header-control)',
            borderColor: 'var(--border-header)',
            color: 'var(--text-header)',
          }}
        >
          {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </button>
      </div>
    </header>
  )
}
