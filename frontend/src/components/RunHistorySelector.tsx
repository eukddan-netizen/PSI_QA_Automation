import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, History, Trash2 } from 'lucide-react'
import { formatDuration, type RunListItem, type RunState } from '../types/run'

interface RunHistorySelectorProps {
  currentRun: RunState | null
  runs: RunListItem[]
  isRunning: boolean
  onSelectRun: (runId: string) => void
  onDeleteRuns: (runIds: string[]) => Promise<void>
}

function getStatusMeta(item: { status: RunListItem['status']; summary: RunListItem['summary'] }) {
  if (item.status === 'running') {
    return { label: '진행중', color: 'var(--status-run)' }
  }
  if (item.status === 'stopped') {
    return { label: '중단', color: 'var(--status-warn)' }
  }
  if (item.summary.failed > 0 || item.status === 'failed') {
    return { label: '오류', color: 'var(--status-fail)' }
  }
  return { label: '완료', color: 'var(--status-pass)' }
}

export function RunHistorySelector({
  currentRun,
  runs,
  isRunning,
  onSelectRun,
  onDeleteRuns,
}: RunHistorySelectorProps) {
  const [open, setOpen] = useState(false)
  const [checkedIds, setCheckedIds] = useState<Set<string>>(() => new Set())
  const [deleting, setDeleting] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const validIds = new Set(runs.filter((r) => r.status !== 'running').map((r) => r.run_id))
    setCheckedIds((prev) => {
      const next = new Set<string>()
      prev.forEach((id) => {
        if (validIds.has(id)) next.add(id)
      })
      return next.size === prev.size ? prev : next
    })
  }, [runs])

  useEffect(() => {
    if (!open) return
    const handleOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handleOutside)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleOutside)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open])

  const deletableRuns = useMemo(() => runs.filter((r) => r.status !== 'running'), [runs])
  const allDeletableChecked =
    deletableRuns.length > 0 && deletableRuns.every((r) => checkedIds.has(r.run_id))

  const activeItem = useMemo(() => {
    if (!currentRun) return null
    return runs.find((r) => r.run_id === currentRun.run_id) ?? currentRun
  }, [currentRun, runs])

  const triggerText = useMemo(() => {
    if (!activeItem) {
      return `실행 이력 선택 (${runs.length}건)`
    }
    const meta = getStatusMeta(activeItem)
    return `[${meta.label}] ${activeItem.started_at.slice(5, 16)} · ${activeItem.title}`
  }, [activeItem, runs.length])

  const toggleCheck = (runId: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev)
      if (next.has(runId)) next.delete(runId)
      else next.add(runId)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (allDeletableChecked) {
      setCheckedIds(new Set())
    } else {
      setCheckedIds(new Set(deletableRuns.map((r) => r.run_id)))
    }
  }

  const handleDeleteSelected = async () => {
    if (checkedIds.size === 0 || deleting) return
    setDeleting(true)
    try {
      await onDeleteRuns(Array.from(checkedIds))
      setCheckedIds(new Set())
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div ref={containerRef} className="relative min-w-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="실행 이력 선택"
        title={triggerText}
        className="inline-flex h-8 min-w-[260px] max-w-[460px] items-center justify-between gap-2 rounded border px-2.5 text-[12px] outline-none transition-opacity hover:opacity-90 cursor-pointer"
        style={{
          backgroundColor: 'var(--bg-header-control)',
          borderColor: open ? 'var(--accent-primary)' : 'var(--border-header)',
          color: activeItem ? 'var(--text-header)' : 'var(--text-header-muted)',
        }}
      >
        <span className="flex items-center gap-1.5 min-w-0">
          <History className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-header-muted)' }} />
          <span className="truncate">{triggerText}</span>
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          style={{ color: 'var(--text-header-muted)' }}
        />
      </button>

      {open && (
        <div
          className="absolute left-0 top-full z-50 mt-1.5 min-w-[540px] max-w-[780px] w-max rounded-md border shadow-xl select-none"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-strong)',
            color: 'var(--text-primary)',
          }}
        >
          {/* Popover Header */}
          <div
            className="flex items-center justify-between gap-4 border-b px-3 py-2 text-[11.5px]"
            style={{
              backgroundColor: 'var(--bg-category-header)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
              저장된 실행 이력{' '}
              <span className="font-mono-code font-normal" style={{ color: 'var(--text-muted)' }}>
                ({runs.length}건)
              </span>
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={deletableRuns.length === 0}
                onClick={toggleSelectAll}
                className="rounded border px-2 py-0.5 text-[11px] transition-opacity hover:opacity-85 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  borderColor: 'var(--border-subtle)',
                  color: 'var(--text-secondary)',
                }}
              >
                {allDeletableChecked ? '선택 해제' : '전체 선택'}
              </button>

              <button
                type="button"
                disabled={checkedIds.size === 0 || deleting || isRunning}
                onClick={handleDeleteSelected}
                className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium transition-opacity hover:opacity-85 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                style={{
                  backgroundColor: checkedIds.size > 0 ? 'var(--status-fail-bg)' : 'var(--bg-surface)',
                  borderColor: checkedIds.size > 0 ? 'var(--status-fail-border)' : 'var(--border-subtle)',
                  color: checkedIds.size > 0 ? 'var(--status-fail)' : 'var(--text-muted)',
                }}
                title="체크된 이력을 DB(runs.db) 및 로그 파일에서 삭제합니다"
              >
                <Trash2 className="h-3 w-3" />
                <span>{deleting ? '삭제중...' : `선택 삭제 (${checkedIds.size})`}</span>
              </button>
            </div>
          </div>

          {/* Runs List */}
          <div className="max-h-[380px] overflow-y-auto divide-y" style={{ borderColor: 'var(--border-row)' }}>
            {runs.map((item) => {
              const meta = getStatusMeta(item)
              const isSelected = currentRun?.run_id === item.run_id
              const isChecked = checkedIds.has(item.run_id)
              const cantDelete = item.status === 'running'

              return (
                <div
                  key={item.run_id}
                  className="flex items-start gap-2.5 px-3 py-2 transition-colors hover:bg-[var(--bg-hover)]"
                  style={{
                    backgroundColor: isSelected ? 'var(--accent-bg)' : 'transparent',
                  }}
                >
                  <button
                    type="button"
                    disabled={cantDelete}
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleCheck(item.run_id)
                    }}
                    aria-label={`${item.title} 삭제 선택`}
                    className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors disabled:opacity-35 disabled:cursor-not-allowed cursor-pointer"
                    style={{
                      backgroundColor: isChecked ? 'var(--accent-primary)' : 'var(--bg-subtle)',
                      borderColor: isChecked ? 'var(--accent-primary)' : 'var(--border-strong)',
                      color: '#ffffff',
                    }}
                  >
                    {isChecked && <Check className="h-3 w-3 stroke-[2.5]" />}
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      onSelectRun(item.run_id)
                      setOpen(false)
                    }}
                    className="flex flex-1 items-start justify-between gap-3 text-left cursor-pointer min-w-0"
                  >
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <div className="flex items-start gap-1.5 text-[12px] leading-snug">
                        <span
                          className="font-mono-code shrink-0 font-semibold"
                          style={{ color: meta.color }}
                        >
                          [{meta.label}]
                        </span>
                        <span
                          className="font-mono-code shrink-0"
                          style={{ color: 'var(--text-muted)' }}
                        >
                          {item.started_at.slice(5, 16)}
                        </span>
                        <span style={{ color: 'var(--text-muted)' }}>·</span>
                        <span
                          className="whitespace-normal break-words font-medium"
                          style={{ color: isSelected ? 'var(--accent-primary)' : 'var(--text-primary)' }}
                        >
                          {item.title}
                        </span>
                      </div>
                    </div>

                    <div
                      className="font-mono-code shrink-0 pt-0.5 text-[11px] flex items-center gap-2"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <span>
                        {item.summary.completed}/{item.summary.total}건
                      </span>
                      {item.summary.duration_sec > 0 && (
                        <span>{formatDuration(item.summary.duration_sec)}</span>
                      )}
                    </div>
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
