import { useState } from 'react'
import {
  FileSpreadsheet,
  FileText,
  Moon,
  Play,
  RotateCcw,
  Shield,
  Square,
  Sun,
  Terminal,
} from 'lucide-react'
import type { CatalogPreset, RunListItem, RunState, RunnerStatus } from '../types/run'

interface TopBarProps {
  run: RunState | null
  runs: RunListItem[]
  presets: CatalogPreset[]
  runner: RunnerStatus
  connected: boolean
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  onSelectRun: (runId: string) => void
  onStartRun: (preset: CatalogPreset) => Promise<void>
  onStopRun: () => Promise<void>
  onClearRuns: () => Promise<void>
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
  onStopRun,
  onClearRuns,
}: TopBarProps) {
  const [selectedPresetId, setSelectedPresetId] = useState<string>('app_all')
  const [launching, setLaunching] = useState(false)

  const activePreset = presets.find((p) => p.id === selectedPresetId) ?? presets[0]
  const canExport = Boolean(run && run.cases.length > 0)
  const completedCount = run?.summary.completed ?? 0
  const totalCount = run?.summary.total ?? 0

  const handleLaunch = async () => {
    if (!activePreset || launching) return
    setLaunching(true)
    try {
      await onStartRun(activePreset)
    } finally {
      setLaunching(false)
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
        backgroundColor: 'var(--bg-surface)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Left: Brand & Live Connection & Run History */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2">
          <div
            className="flex h-7 w-7 items-center justify-center rounded border"
            style={{
              backgroundColor: 'var(--bg-subtle)',
              borderColor: 'var(--border-strong)',
            }}
          >
            <Terminal className="h-3.5 w-3.5" style={{ color: 'var(--text-primary)' }} />
          </div>
          <div className="leading-tight">
            <div className="text-[13px] font-semibold tracking-tight">PSI QA Monitor</div>
            <div className="flex items-center gap-1.5 text-[11px]" style={{ color: 'var(--text-muted)' }}>
              <span
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{
                  backgroundColor: connected ? 'var(--status-pass)' : 'var(--status-fail)',
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

        <div className="h-5 w-px mx-1" style={{ backgroundColor: 'var(--border-subtle)' }} />

        {/* Run Selector & Reset */}
        {runs.length > 0 && (
          <div className="flex items-center gap-1.5">
            <select
              value={run?.run_id ?? ''}
              onChange={(e) => e.target.value && onSelectRun(e.target.value)}
              aria-label="실행 이력 선택"
              className="h-8 max-w-[230px] rounded border px-2 text-[12px] outline-none"
              style={{
                backgroundColor: 'var(--bg-subtle)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
            >
              {runs.map((item) => (
                <option key={item.run_id} value={item.run_id}>
                  [{item.status === 'running' ? '진행중' : item.summary.failed > 0 ? '오류' : '완료'}] {item.started_at.slice(5, 16)} · {item.title}
                </option>
              ))}
            </select>

            <button
              type="button"
              disabled={runner.is_running}
              onClick={onClearRuns}
              title="저장된 이전 테스트 실행 결과 및 로그 초기화"
              className="inline-flex h-8 items-center gap-1 rounded border px-2 text-[11.5px] font-medium transition-colors hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-secondary)',
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
        {/* Preset Launcher */}
        <div className="flex items-center gap-2">
          <select
            value={activePreset?.id ?? ''}
            onChange={(e) => setSelectedPresetId(e.target.value)}
            disabled={runner.is_running}
            aria-label="테스트 실행 대상 선택"
            className="h-8 max-w-[220px] rounded border px-2.5 text-[12px] outline-none disabled:opacity-50"
            style={{
              backgroundColor: 'var(--bg-subtle)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-primary)',
            }}
          >
            {presets.map((p) => (
              <option
                key={p.id}
                value={p.id}
                style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)' }}
              >
                {p.label}
              </option>
            ))}
          </select>

          {runner.is_running ? (
            <button
              type="button"
              onClick={onStopRun}
              className="inline-flex h-8 items-center gap-1.5 rounded border px-3 text-[12px] font-medium transition-colors cursor-pointer"
              style={{
                backgroundColor: 'var(--status-fail-bg)',
                borderColor: 'var(--status-fail-border)',
                color: 'var(--status-fail)',
              }}
            >
              <Square className="h-3 w-3 fill-current" />
              <span>중단</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleLaunch}
              disabled={!activePreset || launching}
              className="inline-flex h-8 items-center gap-1.5 rounded px-3 text-[12px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40 cursor-pointer"
              style={{ backgroundColor: 'var(--accent-primary)' }}
            >
              <Play className="h-3 w-3 fill-current" />
              <span>{launching ? '시작중...' : '테스트 실행'}</span>
            </button>
          )}
        </div>

        <div className="h-5 w-px mx-0.5" style={{ backgroundColor: 'var(--border-subtle)' }} />

        {/* Export Snapshot Buttons (Top-Right Requirement) */}
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
            className="inline-flex h-8 items-center gap-1.5 rounded border px-2.5 text-[12px] font-medium transition-colors hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border-strong)',
              color: 'var(--text-primary)',
            }}
          >
            <FileSpreadsheet className="h-3.5 w-3.5" style={{ color: 'var(--status-pass)' }} />
            <span>Excel</span>
          </button>

          <button
            type="button"
            disabled={!canExport}
            onClick={() => handleDownload('docx')}
            className="inline-flex h-8 items-center gap-1.5 rounded border px-2.5 text-[12px] font-medium transition-colors hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border-strong)',
              color: 'var(--text-primary)',
            }}
          >
            <FileText className="h-3.5 w-3.5" style={{ color: 'var(--accent-primary)' }} />
            <span>Word</span>
          </button>
        </div>

        {/* Theme Toggle */}
        <button
          type="button"
          onClick={onToggleTheme}
          title={theme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
          className="flex h-8 w-8 items-center justify-center rounded border transition-colors cursor-pointer"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-subtle)',
            color: 'var(--text-secondary)',
          }}
        >
          {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
        </button>
      </div>
    </header>
  )
}
