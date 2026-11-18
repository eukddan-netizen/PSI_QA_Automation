import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronRight, Search } from 'lucide-react'
import type { DomainGroup, TestStatus } from '../types/run'
import { StatusDot } from './StatusBadge'

interface TestTreePanelProps {
  runId?: string | null
  domains: DomainGroup[]
  activeNodeId?: string | null
  statusFilter: 'all' | 'failed' | 'running' | 'passed'
  onChangeStatusFilter: (f: 'all' | 'failed' | 'running' | 'passed') => void
  onSelectCase: (catKey: string, nodeid: string) => void
}

export function TestTreePanel({
  runId,
  domains,
  activeNodeId,
  statusFilter,
  onChangeStatusFilter,
  onSelectCase,
}: TestTreePanelProps) {
  const [query, setQuery] = useState('')
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(() => new Set())
  const [expandedCats, setExpandedCats] = useState<Set<string>>(() => new Set())
  const seenRunIdRef = useRef<string | null | undefined>(undefined)
  const autoOpenedCatsRef = useRef<Set<string>>(new Set())
  const autoOpenedDomainsRef = useRef<Set<string>>(new Set())

  // Start all tree toggles closed on a new run, then auto-open only executed/running branches
  useEffect(() => {
    if (seenRunIdRef.current !== runId) {
      seenRunIdRef.current = runId
      autoOpenedCatsRef.current = new Set()
      autoOpenedDomainsRef.current = new Set()
      setExpandedDomains(new Set())
      setExpandedCats(new Set())
    }

    const newDomains: string[] = []
    const newCats: string[] = []

    for (const dom of domains) {
      const domActive = dom.running > 0 || dom.passed > 0 || dom.failed > 0 || dom.skipped > 0
      if (domActive && !autoOpenedDomainsRef.current.has(dom.domain)) {
        autoOpenedDomainsRef.current.add(dom.domain)
        newDomains.push(dom.domain)
      }
      for (const cat of dom.categories) {
        const catActive = cat.running > 0 || cat.passed > 0 || cat.failed > 0 || cat.skipped > 0
        if (catActive && !autoOpenedCatsRef.current.has(cat.key)) {
          autoOpenedCatsRef.current.add(cat.key)
          newCats.push(cat.key)
        }
      }
    }

    if (newDomains.length > 0) {
      setExpandedDomains((prev) => {
        const next = new Set(prev)
        newDomains.forEach((d) => next.add(d))
        return next
      })
    }
    if (newCats.length > 0) {
      setExpandedCats((prev) => {
        const next = new Set(prev)
        newCats.forEach((c) => next.add(c))
        return next
      })
    }
  }, [runId, domains])

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
      className="flex h-full w-[310px] shrink-0 flex-col border-r select-none"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Search + Quick Filters */}
      <div className="space-y-2 border-b p-3" style={{ borderColor: 'var(--border-subtle)' }}>
        <div
          className="flex h-8 items-center gap-1.5 rounded border px-2"
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
      <div className="flex-1 overflow-y-auto px-2 py-2 text-[12px]">
        {filteredDomains.length === 0 ? (
          <div className="px-2 py-8 text-center text-[12px]" style={{ color: 'var(--text-muted)' }}>
            표시할 테스트 항목이 없습니다.
          </div>
        ) : (
          filteredDomains.map((dom) => {
            const domExpanded = forceExpandForFilter || expandedDomains.has(dom.domain)
            return (
              <div key={dom.domain} className="mb-3">
                {/* Level 1: 대분류 */}
                <button
                  type="button"
                  onClick={() => toggleDomain(dom.domain)}
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
                    <span className="truncate">{dom.title}</span>
                  </span>
                  <span className="font-mono-code text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    {dom.passed + dom.failed + dom.skipped}/{dom.total}
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
                              <span className="truncate font-medium">{cat.title}</span>
                            </span>
                            <CategoryMiniCounter
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
                                return (
                                  <button
                                    key={tc.nodeid}
                                    type="button"
                                    onClick={() => onSelectCase(cat.key, tc.nodeid)}
                                    title={`${tc.tc_id ? `[${tc.tc_id}] ` : ''}${tc.title}\n(${tc.id})`}
                                    className="flex w-full items-center justify-between rounded px-2 py-1 text-left transition-colors cursor-pointer"
                                    style={{
                                      backgroundColor: isActive ? 'var(--accent-bg)' : 'transparent',
                                      color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                    }}
                                  >
                                    <span className="flex items-center gap-1.5 min-w-0">
                                      <StatusDot status={tc.status} />
                                      <span className="truncate text-[11.5px]">
                                        {tc.tc_id ? (
                                          <span className="font-mono-code mr-1 opacity-70">{tc.tc_id}</span>
                                        ) : null}
                                        {tc.title}
                                      </span>
                                    </span>
                                    {tc.duration != null && tc.status !== 'running' && tc.status !== 'pending' && (
                                      <span
                                        className="font-mono-code ml-1 shrink-0 text-[10px]"
                                        style={{ color: 'var(--text-muted)' }}
                                      >
                                        {tc.duration.toFixed(1)}s
                                      </span>
                                    )}
                                  </button>
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
    </aside>
  )
}

function CategoryMiniCounter({
  passed,
  failed,
  total,
  status,
}: {
  passed: number
  failed: number
  total: number
  status: TestStatus
}) {
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
