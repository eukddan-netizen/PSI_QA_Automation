import { useEffect, useMemo, useRef, useState } from 'react'
import { Calendar, Check, ChevronDown, ChevronRight, History, Minus, Trash2 } from 'lucide-react'
import { formatDuration, type RunListItem, type RunState } from '../types/run'

interface RunHistorySelectorProps {
  currentRun: RunState | null
  runs: RunListItem[]
  isRunning: boolean
  onSelectRun: (runId: string) => void
  onDeleteRuns: (runIds: string[]) => Promise<void>
}

interface DateGroup {
  dateKey: string
  dateLabel: string
  items: RunListItem[]
  deletableIds: string[]
  hasCurrentRun: boolean
  hasRunning: boolean
  failedCount: number
}

const WEEKDAYS_KO = ['일', '월', '화', '수', '목', '금', '토'] as const

function extractDateKey(startedAt: string): string {
  const m = (startedAt || '').match(/^(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : '날짜 미상'
}

function extractTimeLabel(startedAt: string): string {
  const m = (startedAt || '').match(/\d{4}-\d{2}-\d{2}[T\s](\d{2}:\d{2})/)
  return m ? m[1] : startedAt.slice(5, 16)
}

function formatDateHeading(dateKey: string): string {
  const m = dateKey.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return dateKey
  const dt = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  const weekday = Number.isNaN(dt.getTime()) ? '' : ` (${WEEKDAYS_KO[dt.getDay()]})`
  return `${dateKey}${weekday}`
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
  const [expandedDates, setExpandedDates] = useState<Set<string>>(() => new Set())
  const [checkedIds, setCheckedIds] = useState<Set<string>>(() => new Set())
  const [deleting, setDeleting] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  const handleToggleOpen = () => {
    setOpen((prev) => {
      const next = !prev
      if (next) {
        // 드롭다운을 열 때마다 날짜별 토글은 닫힌 상태를 디폴트로 초기화
        setExpandedDates(new Set())
      }
      return next
    })
  }

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

  const dateGroups = useMemo<DateGroup[]>(() => {
    const map = new Map<string, RunListItem[]>()
    for (const item of runs) {
      const key = extractDateKey(item.started_at)
      const list = map.get(key)
      if (list) list.push(item)
      else map.set(key, [item])
    }
    return Array.from(map.entries())
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([dateKey, items]) => ({
        dateKey,
        dateLabel: formatDateHeading(dateKey),
        items,
        deletableIds: items.filter((r) => r.status !== 'running').map((r) => r.run_id),
        hasCurrentRun: Boolean(currentRun && items.some((r) => r.run_id === currentRun.run_id)),
        hasRunning: items.some((r) => r.status === 'running'),
        failedCount: items.filter((r) => r.summary.failed > 0 || r.status === 'failed').length,
      }))
  }, [runs, currentRun])

  const toggleDate = (dateKey: string) => {
    setExpandedDates((prev) => {
      const next = new Set(prev)
      if (next.has(dateKey)) next.delete(dateKey)
      else next.add(dateKey)
      return next
    })
  }

  const toggleDateCheck = (group: DateGroup) => {
    if (group.deletableIds.length === 0) return
    setCheckedIds((prev) => {
      const next = new Set(prev)
      const allGroupChecked = group.deletableIds.every((id) => next.has(id))
      if (allGroupChecked) {
        group.deletableIds.forEach((id) => next.delete(id))
      } else {
        group.deletableIds.forEach((id) => next.add(id))
      }
      return next
    })
  }

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
        onClick={handleToggleOpen}
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

          {/* Date-grouped Runs List */}
          <div className="max-h-[420px] overflow-y-auto divide-y" style={{ borderColor: 'var(--border-subtle)' }}>
            {dateGroups.length === 0 ? (
              <div className="px-4 py-6 text-center text-[12px]" style={{ color: 'var(--text-muted)' }}>
                저장된 실행 이력이 없습니다.
              </div>
            ) : (
              dateGroups.map((group) => {
                const isExpanded = expandedDates.has(group.dateKey)
                const checkedInGroup = group.deletableIds.filter((id) => checkedIds.has(id)).length
                const allGroupChecked =
                  group.deletableIds.length > 0 && checkedInGroup === group.deletableIds.length
                const someGroupChecked = checkedInGroup > 0 && !allGroupChecked

                return (
                  <div key={group.dateKey}>
                    {/* Date Group Toggle Header */}
                    <div
                      className="flex items-center gap-2 px-3 py-2 transition-colors hover:bg-[var(--bg-hover)]"
                      style={{
                        backgroundColor: isExpanded ? 'var(--bg-category-header)' : 'var(--bg-surface)',
                      }}
                    >
                      <button
                        type="button"
                        disabled={group.deletableIds.length === 0}
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleDateCheck(group)
                        }}
                        aria-label={`${group.dateLabel} 전체 삭제 선택`}
                        className="flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors disabled:opacity-35 disabled:cursor-not-allowed cursor-pointer"
                        style={{
                          backgroundColor:
                            allGroupChecked || someGroupChecked ? 'var(--accent-primary)' : 'var(--bg-subtle)',
                          borderColor:
                            allGroupChecked || someGroupChecked ? 'var(--accent-primary)' : 'var(--border-strong)',
                          color: '#ffffff',
                        }}
                      >
                        {allGroupChecked && <Check className="h-3 w-3 stroke-[2.5]" />}
                        {someGroupChecked && <Minus className="h-3 w-3 stroke-[2.5]" />}
                      </button>

                      <button
                        type="button"
                        onClick={() => toggleDate(group.dateKey)}
                        aria-expanded={isExpanded}
                        className="flex flex-1 items-center justify-between gap-3 text-left cursor-pointer min-w-0"
                      >
                        <span className="flex items-center gap-1.5 min-w-0 text-[12px] font-semibold">
                          {isExpanded ? (
                            <ChevronDown className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
                          ) : (
                            <ChevronRight className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
                          )}
                          <Calendar className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
                          <span
                            className="font-mono-code"
                            style={{ color: group.hasCurrentRun ? 'var(--accent-primary)' : 'var(--text-primary)' }}
                          >
                            {group.dateLabel}
                          </span>
                          {group.hasCurrentRun && (
                            <span
                              className="rounded px-1.5 py-0.5 text-[10px] font-medium"
                              style={{
                                backgroundColor: 'var(--accent-bg)',
                                color: 'var(--accent-primary)',
                              }}
                            >
                              현재
                            </span>
                          )}
                        </span>

                        <span className="font-mono-code flex shrink-0 items-center gap-2 text-[11px]">
                          {group.hasRunning && (
                            <span style={{ color: 'var(--status-run)' }}>진행중</span>
                          )}
                          {group.failedCount > 0 && (
                            <span style={{ color: 'var(--status-fail)' }}>오류 {group.failedCount}</span>
                          )}
                          <span style={{ color: 'var(--text-muted)' }}>{group.items.length}건</span>
                        </span>
                      </button>
                    </div>

                    {/* Runs belonging to this date */}
                    {isExpanded && (
                      <div
                        className="divide-y border-t"
                        style={{
                          borderColor: 'var(--border-row)',
                          backgroundColor: 'var(--bg-surface)',
                        }}
                      >
                        {group.items.map((item) => {
                          const meta = getStatusMeta(item)
                          const isSelected = currentRun?.run_id === item.run_id
                          const isChecked = checkedIds.has(item.run_id)
                          const cantDelete = item.status === 'running'

                          return (
                            <div
                              key={item.run_id}
                              className="flex items-start gap-2.5 pl-8 pr-3 py-2 transition-colors hover:bg-[var(--bg-hover)]"
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
                                      {extractTimeLabel(item.started_at)}
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
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
