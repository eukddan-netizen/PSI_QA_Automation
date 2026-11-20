import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2, Play, RefreshCw, RotateCw, Search } from 'lucide-react'
import {
  formatDuration,
  type DomainGroup,
  type RunStatus,
  type TestCaseState,
  type TestStatus,
} from '../types/run'
import { StatusDot } from './StatusBadge'

interface TestTreePanelProps {
  runId?: string | null
  runStatus?: RunStatus | null
  runBatchSeq?: number
  domains: DomainGroup[]
  runCaseNodeIds: Set<string>
  activeNodeId?: string | null
  isRunning: boolean
  catalogLoading?: boolean
  statusFilter: 'all' | 'failed' | 'running' | 'passed'
  onChangeStatusFilter: (f: 'all' | 'failed' | 'running' | 'passed') => void
  onSelectCase: (catKey: string, nodeid: string) => void
  onRunSingleCase: (tc: TestCaseState) => Promise<void> | void
  onRefreshCatalog?: () => void
}

export function TestTreePanel({
  runId,
  runStatus,
  runBatchSeq = 0,
  domains,
  runCaseNodeIds,
  activeNodeId,
  isRunning,
  catalogLoading = false,
  statusFilter,
  onChangeStatusFilter,
  onSelectCase,
  onRunSingleCase,
  onRefreshCatalog,
}: TestTreePanelProps) {
  const [query, setQuery] = useState('')
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(() => new Set())
  const [expandedCats, setExpandedCats] = useState<Set<string>>(() => new Set())
  const [launchingNodeId, setLaunchingNodeId] = useState<string | null>(null)
  const [hoverTooltip, setHoverTooltip] = useState<{
    text: string
    subtext?: string
    top: number
    left: number
  } | null>(null)
  const asideRef = useRef<HTMLElement | null>(null)
  const seenRunIdRef = useRef<string | null | undefined>(undefined)
  const initExpandedCatalogRef = useRef(false)
  const lastBatchSeqRef = useRef<number>(runBatchSeq)
  const prevRunStatusRef = useRef<RunStatus | null | undefined>(runStatus)
  const activeBatchOnlyRef = useRef(false)
  const baselineDomDoneRef = useRef<Map<string, number>>(new Map())
  const baselineCatDoneRef = useRef<Map<string, number>>(new Map())
  const autoOpenedCatsRef = useRef<Set<string>>(new Set())
  const autoOpenedDomainsRef = useRef<Set<string>>(new Set())
  const wasRunningCatsRef = useRef<Set<string>>(new Set())
  const autoClosedCatsRef = useRef<Set<string>>(new Set())
  const wasRunningDomainsRef = useRef<Set<string>>(new Set())
  const autoClosedDomainsRef = useRef<Set<string>>(new Set())

  const showTruncatedTooltip = (
    e: React.MouseEvent<HTMLElement>,
    text: string,
    subtext?: string,
  ) => {
    const target = e.currentTarget
    const truncEl = target.querySelector<HTMLElement>('[data-trunc-label]')
    if (truncEl && truncEl.scrollWidth <= truncEl.clientWidth + 1) {
      setHoverTooltip(null)
      return
    }
    const rowRect = target.getBoundingClientRect()
    const asideRect = asideRef.current?.getBoundingClientRect()
    const left = asideRect ? asideRect.right + 8 : rowRect.right + 8
    const clampedTop = Math.max(48, Math.min(window.innerHeight - 48, rowRect.top + rowRect.height / 2))
    setHoverTooltip({ text, subtext, top: clampedTop, left })
  }

  const hideTooltip = () => setHoverTooltip(null)

  const handleRunSingle = async (tc: TestCaseState) => {
    if (isRunning || launchingNodeId) return
    setLaunchingNodeId(tc.nodeid)
    try {
      await onRunSingleCase(tc)
    } finally {
      setLaunchingNodeId(null)
    }
  }

  // Start all tree toggles closed on a new run or new batch, then auto-open only newly active branches.
  // In catalog-browsing mode (no active run), expand top-level domains so categories are immediately visible.
  useEffect(() => {
    const isNewRunId = seenRunIdRef.current !== runId
    const isNewBatchOnSameRun =
      !isNewRunId &&
      Boolean(runId) &&
      (lastBatchSeqRef.current !== runBatchSeq ||
        (prevRunStatusRef.current !== 'running' && runStatus === 'running'))

    if (isNewRunId) {
      seenRunIdRef.current = runId
      lastBatchSeqRef.current = runBatchSeq
      prevRunStatusRef.current = runStatus
      activeBatchOnlyRef.current = false
      baselineDomDoneRef.current = new Map()
      baselineCatDoneRef.current = new Map()
      autoOpenedCatsRef.current = new Set()
      autoOpenedDomainsRef.current = new Set()
      wasRunningCatsRef.current = new Set()
      autoClosedCatsRef.current = new Set()
      wasRunningDomainsRef.current = new Set()
      autoClosedDomainsRef.current = new Set()
      if (!runId) {
        initExpandedCatalogRef.current = domains.length > 0
        setExpandedDomains(new Set(domains.map((d) => d.domain)))
        setExpandedCats(new Set())
      } else {
        initExpandedCatalogRef.current = false
        setExpandedDomains(new Set())
        setExpandedCats(new Set())
      }
    } else if (isNewBatchOnSameRun) {
      lastBatchSeqRef.current = runBatchSeq
      prevRunStatusRef.current = runStatus
      activeBatchOnlyRef.current = true
      baselineDomDoneRef.current = new Map(
        domains.map((dom) => [dom.domain, dom.passed + dom.failed + dom.skipped]),
      )
      baselineCatDoneRef.current = new Map(
        domains.flatMap((dom) =>
          dom.categories.map((cat) => [cat.key, cat.passed + cat.failed + cat.skipped] as const),
        ),
      )
      autoOpenedCatsRef.current = new Set()
      autoOpenedDomainsRef.current = new Set()
      wasRunningCatsRef.current = new Set()
      autoClosedCatsRef.current = new Set()
      wasRunningDomainsRef.current = new Set()
      autoClosedDomainsRef.current = new Set()
      setExpandedDomains(new Set())
      setExpandedCats(new Set())
    } else {
      lastBatchSeqRef.current = runBatchSeq
      prevRunStatusRef.current = runStatus
    }

    if (!runId) {
      if (!initExpandedCatalogRef.current && domains.length > 0) {
        initExpandedCatalogRef.current = true
        setExpandedDomains(new Set(domains.map((d) => d.domain)))
      }
      return
    }

    const activeRunningDomains = new Set(domains.filter((d) => d.running > 0).map((d) => d.domain))
    const activeRunningCats = new Set(
      domains.flatMap((d) => d.categories.filter((c) => c.running > 0).map((c) => c.key)),
    )
    const isRunFinished = runStatus !== 'running'

    const newDomains: string[] = []
    const closeDomains: string[] = []
    const newCats: string[] = []
    const closeCats: string[] = []

    for (const dom of domains) {
      const domDone = dom.passed + dom.failed + dom.skipped
      if (dom.running > 0) {
        wasRunningDomainsRef.current.add(dom.domain)
      }

      let domActive: boolean
      if (activeBatchOnlyRef.current) {
        let domBase = baselineDomDoneRef.current.get(dom.domain) ?? 0
        if (domDone < domBase) {
          baselineDomDoneRef.current.set(dom.domain, domDone)
          domBase = domDone
        }
        domActive = dom.running > 0 || domDone > domBase
      } else {
        domActive = dom.running > 0 || (!isRunFinished && domDone > 0)
      }

      if (domActive && !autoOpenedDomainsRef.current.has(dom.domain)) {
        autoOpenedDomainsRef.current.add(dom.domain)
        newDomains.push(dom.domain)
      }

      const otherDomainRunning = Array.from(activeRunningDomains).some((d) => d !== dom.domain)
      if (
        wasRunningDomainsRef.current.has(dom.domain) &&
        dom.running === 0 &&
        !autoClosedDomainsRef.current.has(dom.domain) &&
        (domDone >= dom.total || otherDomainRunning || isRunFinished)
      ) {
        autoClosedDomainsRef.current.add(dom.domain)
        closeDomains.push(dom.domain)
      }

      for (const cat of dom.categories) {
        const catDone = cat.passed + cat.failed + cat.skipped
        if (cat.running > 0) {
          wasRunningCatsRef.current.add(cat.key)
        }

        let catActive: boolean
        if (activeBatchOnlyRef.current) {
          let catBase = baselineCatDoneRef.current.get(cat.key) ?? 0
          if (catDone < catBase) {
            baselineCatDoneRef.current.set(cat.key, catDone)
            catBase = catDone
          }
          catActive = cat.running > 0 || catDone > catBase
        } else {
          catActive = cat.running > 0 || (!isRunFinished && catDone > 0)
        }

        if (catActive && !autoOpenedCatsRef.current.has(cat.key)) {
          autoOpenedCatsRef.current.add(cat.key)
          newCats.push(cat.key)
        }

        const otherCatRunning = Array.from(activeRunningCats).some((k) => k !== cat.key)
        if (
          wasRunningCatsRef.current.has(cat.key) &&
          cat.running === 0 &&
          !autoClosedCatsRef.current.has(cat.key) &&
          (catDone >= cat.total || otherCatRunning || isRunFinished)
        ) {
          autoClosedCatsRef.current.add(cat.key)
          closeCats.push(cat.key)
        }
      }
    }

    if (newDomains.length > 0 || closeDomains.length > 0) {
      setExpandedDomains((prev) => {
        const next = new Set(prev)
        newDomains.forEach((d) => next.add(d))
        closeDomains.forEach((d) => next.delete(d))
        return next
      })
    }
    if (newCats.length > 0 || closeCats.length > 0) {
      setExpandedCats((prev) => {
        const next = new Set(prev)
        newCats.forEach((c) => next.add(c))
        closeCats.forEach((c) => next.delete(c))
        return next
      })
    }
  }, [runId, runStatus, runBatchSeq, domains])

  const filteredDomains = useMemo(() => {
    const q = query.trim().toLowerCase()
    return domains
      .map((dom) => {
        const categories = dom.categories
          .map((cat) => {
            const cases = cat.cases.filter((tc) => {
              if (statusFilter === 'failed' && tc.status !== 'failed' && tc.status !== 'error') return false
              if (statusFilter === 'running' && tc.status !== 'running') return false
              if (statusFilter === 'passed' && tc.status !== 'passed') return false
              if (!q) return true
              return (
                (tc.tc_id?.toLowerCase().includes(q) ?? false) ||
                tc.id.toLowerCase().includes(q) ||
                tc.title.toLowerCase().includes(q) ||
                cat.title.toLowerCase().includes(q) ||
                (tc.subcategory_title?.toLowerCase().includes(q) ?? false)
              )
            })
            return { ...cat, cases }
          })
          .filter((cat) => cat.cases.length > 0)
        return { ...dom, categories }
      })
      .filter((dom) => dom.categories.length > 0)
  }, [domains, query, statusFilter])

  const toggleDomain = (domain: string) => {
    setExpandedDomains((s) => {
      const next = new Set(s)
      if (next.has(domain)) next.delete(domain)
      else next.add(domain)
      return next
    })
  }

  const toggleCat = (key: string) => {
    setExpandedCats((s) => {
      const next = new Set(s)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const forceExpandForFilter = query.trim().length > 0 || statusFilter !== 'all'

  const filterButtons: Array<{ id: 'all' | 'running' | 'failed' | 'passed'; label: string }> = [
    { id: 'all', label: '전체' },
    { id: 'running', label: '실행중' },
    { id: 'failed', label: '오류' },
    { id: 'passed', label: '정상' },
  ]

  return (
    <aside
      ref={asideRef}
      onMouseLeave={hideTooltip}
      className="flex h-full w-[310px] shrink-0 flex-col border-r select-none"
      style={{
        backgroundColor: 'var(--bg-sidebar)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Search + Quick Filters */}
      <div
        className="space-y-2 border-b p-3"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="flex items-center gap-1.5">
          <div
            className="flex h-8 flex-1 items-center gap-1.5 rounded border px-2"
            style={{
              backgroundColor: 'var(--bg-subtle)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <Search className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="테스트 항목 / TC 검색..."
              className="w-full bg-transparent text-[12px] outline-none placeholder:opacity-60"
              style={{ color: 'var(--text-primary)' }}
            />
          </div>
          {onRefreshCatalog && (
            <button
              type="button"
              onClick={onRefreshCatalog}
              disabled={catalogLoading || isRunning}
              title="테스트 항목 목록 다시 수집"
              aria-label="테스트 항목 목록 새로고침"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded border transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
              style={{
                backgroundColor: 'var(--bg-subtle)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-secondary)',
              }}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${catalogLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>

        <div className="grid grid-cols-4 gap-1">
          {filterButtons.map((btn) => {
            const active = statusFilter === btn.id
            return (
              <button
                key={btn.id}
                type="button"
                onClick={() => onChangeStatusFilter(btn.id)}
                className="h-6 rounded text-[11px] font-medium transition-colors cursor-pointer border"
                style={{
                  backgroundColor: active ? 'var(--accent-bg)' : 'transparent',
                  borderColor: active ? 'var(--accent-primary)' : 'var(--border-subtle)',
                  color: active ? 'var(--accent-primary)' : 'var(--text-secondary)',
                }}
              >
                {btn.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* 3-Level Hierarchy Explorer */}
      <div
        onScroll={hideTooltip}
        className="flex-1 overflow-y-auto px-2 py-2 text-[12px]"
      >
        {catalogLoading && domains.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center gap-2 px-2 py-10 text-center text-[12px]"
            style={{ color: 'var(--text-muted)' }}
          >
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>테스트 항목 목록 수집 중...</span>
          </div>
        ) : filteredDomains.length === 0 ? (
          <div className="px-2 py-8 text-center text-[12px]" style={{ color: 'var(--text-muted)' }}>
            표시할 테스트 항목이 없습니다.
          </div>
        ) : (
          filteredDomains.map((dom) => {
            const domExpanded = forceExpandForFilter || expandedDomains.has(dom.domain)
            const domDone = dom.passed + dom.failed + dom.skipped
            return (
              <div key={dom.domain} className="mb-3">
                {/* Level 1: 대분류 */}
                <button
                  type="button"
                  onClick={() => toggleDomain(dom.domain)}
                  onMouseEnter={(e) => showTruncatedTooltip(e, dom.title)}
                  onMouseLeave={hideTooltip}
                  className="flex w-full items-center justify-between rounded px-1.5 py-1.5 text-left font-semibold transition-colors hover:opacity-85 cursor-pointer"
                  style={{ color: 'var(--text-primary)' }}
                >
                  <span className="flex items-center gap-1.5 truncate">
                    {domExpanded ? (
                      <ChevronDown className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
                    )}
                    <StatusDot status={dom.status} />
                    <span data-trunc-label className="truncate">{dom.title}</span>
                  </span>
                  <span className="font-mono-code shrink-0 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    {runId ? `${domDone}/${dom.total}` : `${dom.total}건`}
                  </span>
                </button>

                {domExpanded && (
                  <div className="mt-0.5 space-y-1 pl-2">
                    {dom.categories.map((cat) => {
                      const catExpanded = forceExpandForFilter || expandedCats.has(cat.key)
                      return (
                        <div key={cat.key}>
                          {/* Level 2: 중분류 */}
                          <button
                            type="button"
                            onClick={() => toggleCat(cat.key)}
                            onMouseEnter={(e) => showTruncatedTooltip(e, cat.title)}
                            onMouseLeave={hideTooltip}
                            className="flex w-full items-center justify-between rounded px-1.5 py-1 text-left transition-colors cursor-pointer"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            <span className="flex items-center gap-1.5 truncate">
                              {catExpanded ? (
                                <ChevronDown className="h-3 w-3 shrink-0" />
                              ) : (
                                <ChevronRight className="h-3 w-3 shrink-0" />
                              )}
                              <StatusDot status={cat.status} />
                              <span data-trunc-label className="truncate font-medium">{cat.title}</span>
                            </span>
                            <CategoryMiniCounter
                              hasRun={Boolean(runId)}
                              passed={cat.passed}
                              failed={cat.failed}
                              total={cat.total}
                              status={cat.status}
                            />
                          </button>

                          {catExpanded && (
                            <div
                              className="ml-3 mt-0.5 space-y-0.5 border-l pl-2"
                              style={{ borderColor: 'var(--border-subtle)' }}
                            >
                              {cat.cases.map((tc) => {
                                const isActive = tc.nodeid === activeNodeId
                                const inCurrentRun = runCaseNodeIds.has(tc.nodeid)
                                const isFailure = tc.status === 'failed' || tc.status === 'error'
                                const isLaunchingThis = launchingNodeId === tc.nodeid
                                const fullLabel = `${tc.tc_id ? `[${tc.tc_id}] ` : ''}${tc.title}`
                                return (
                                  <div
                                    key={tc.nodeid}
                                    className="group flex w-full items-center gap-1 rounded px-1.5 py-1 transition-colors hover:bg-[var(--bg-hover)]"
                                    style={{
                                      backgroundColor: isActive ? 'var(--accent-bg)' : undefined,
                                    }}
                                  >
                                    <button
                                      type="button"
                                      onClick={() => {
                                        if (inCurrentRun) {
                                          onSelectCase(cat.key, tc.nodeid)
                                        }
                                      }}
                                      onMouseEnter={(e) =>
                                        showTruncatedTooltip(
                                          e,
                                          fullLabel,
                                          inCurrentRun ? tc.id : `${tc.id} · 우측 ▶ 버튼으로 개별 실행`,
                                        )
                                      }
                                      onMouseLeave={hideTooltip}
                                      className={`flex min-w-0 flex-1 items-center gap-1.5 text-left ${inCurrentRun ? 'cursor-pointer' : 'cursor-default'}`}
                                      style={{
                                        color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                      }}
                                    >
                                      <StatusDot status={tc.status} />
                                      <span data-trunc-label className="truncate text-[11.5px]">
                                        {tc.tc_id ? (
                                          <span className="font-mono-code mr-1 opacity-70">{tc.tc_id}</span>
                                        ) : null}
                                        {tc.title}
                                      </span>
                                    </button>

                                    {inCurrentRun &&
                                      tc.duration != null &&
                                      tc.status !== 'running' &&
                                      tc.status !== 'pending' && (
                                        <span
                                          className="font-mono-code shrink-0 text-[10px]"
                                          style={{ color: 'var(--text-muted)' }}
                                        >
                                          {tc.duration >= 60 ? formatDuration(tc.duration) : `${tc.duration.toFixed(1)}초`}
                                        </span>
                                      )}

                                    <button
                                      type="button"
                                      disabled={isRunning || launchingNodeId !== null}
                                      onClick={(e) => {
                                        e.stopPropagation()
                                        void handleRunSingle(tc)
                                      }}
                                      title={
                                        isRunning
                                          ? '다른 테스트가 실행 중입니다'
                                          : isFailure
                                            ? '이 실패 항목만 다시 실행'
                                            : inCurrentRun
                                              ? '이 테스트 항목만 다시 실행'
                                              : '이 테스트 항목만 개별 실행'
                                      }
                                      aria-label={`${tc.tc_id || tc.title} 개별 실행`}
                                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-all disabled:cursor-not-allowed disabled:opacity-30 cursor-pointer opacity-75 group-hover:opacity-100"
                                      style={{
                                        backgroundColor: isFailure ? 'var(--status-fail-bg)' : 'var(--bg-surface)',
                                        borderColor: isFailure ? 'var(--status-fail-border)' : 'var(--border-subtle)',
                                        color: isFailure ? 'var(--status-fail)' : 'var(--accent-primary)',
                                      }}
                                    >
                                      {isLaunchingThis ? (
                                        <Loader2 className="h-2.5 w-2.5 animate-spin" />
                                      ) : isFailure ? (
                                        <RotateCw className="h-2.5 w-2.5" />
                                      ) : (
                                        <Play className="h-2.5 w-2.5 fill-current" />
                                      )}
                                    </button>
                                  </div>
                                )
                              })}
                            </div>
                          )}
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

      {/* Truncated label floating tooltip (fixed so sidebar overflow never clips it) */}
      {hoverTooltip && (
        <div
          role="tooltip"
          className="pointer-events-none fixed z-50 max-w-[380px] -translate-y-1/2 rounded-md border px-2.5 py-1.5 text-[11.5px] leading-snug shadow-lg"
          style={{
            top: `${hoverTooltip.top}px`,
            left: `${hoverTooltip.left}px`,
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-strong)',
            color: 'var(--text-primary)',
          }}
        >
          <div className="whitespace-normal break-words font-medium">{hoverTooltip.text}</div>
          {hoverTooltip.subtext && (
            <div
              className="mt-0.5 whitespace-normal break-all font-mono-code text-[10.5px]"
              style={{ color: 'var(--text-muted)' }}
            >
              {hoverTooltip.subtext}
            </div>
          )}
        </div>
      )}
    </aside>
  )
}

function CategoryMiniCounter({
  hasRun,
  passed,
  failed,
  total,
  status,
}: {
  hasRun: boolean
  passed: number
  failed: number
  total: number
  status: TestStatus
}) {
  if (!hasRun) {
    return (
      <span className="font-mono-code ml-1 shrink-0 text-[10.5px]" style={{ color: 'var(--text-muted)' }}>
        {total}건
      </span>
    )
  }
  return (
    <span className="font-mono-code ml-1 shrink-0 text-[10.5px]" style={{ color: 'var(--text-muted)' }}>
      {failed > 0 ? (
        <span style={{ color: 'var(--status-fail)' }}>{failed} err</span>
      ) : status === 'passed' ? (
        <span style={{ color: 'var(--status-pass)' }}>
          {passed}/{total}
        </span>
      ) : (
        <span>
          {passed}/{total}
        </span>
      )}
    </span>
  )
}
