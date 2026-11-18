import { useEffect, useRef } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Crosshair,
  FolderOpen,
  Minimize2,
  Maximize2,
  Terminal,
} from 'lucide-react'
import type { CategoryGroup, DomainGroup, LogLine, RunState, TestCaseState } from '../types/run'
import { StatusBadge, StatusDot } from './StatusBadge'

interface ExecutionStreamProps {
  run: RunState | null
  domains: DomainGroup[]
  statusFilter: 'all' | 'failed' | 'running' | 'passed'
  autoFollow: boolean
  expandedCategories: Set<string>
  expandedCases: Set<string>
  onToggleAutoFollow: (val: boolean) => void
  onToggleCategory: (catKey: string) => void
  onToggleCase: (nodeid: string) => void
  onExpandAll: () => void
  onCollapsePassed: () => void
  registerCaseRef: (nodeid: string, el: HTMLDivElement | null) => void
}

export function ExecutionStream({
  run,
  domains,
  statusFilter,
  autoFollow,
  expandedCategories,
  expandedCases,
  onToggleAutoFollow,
  onToggleCategory,
  onToggleCase,
  onExpandAll,
  onCollapsePassed,
  registerCaseRef,
}: ExecutionStreamProps) {
  const activeCase = run?.cases.find((c) => c.nodeid === run.active_nodeid) ?? null

  if (!run) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center p-8 text-center">
        <div
          className="max-w-md rounded-lg border p-6"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <Terminal className="mx-auto mb-3 h-7 w-7" style={{ color: 'var(--text-muted)' }} />
          <h2 className="text-[14px] font-semibold">QA 자동화 실시간 로그 대기 중</h2>
          <p className="mt-1.5 text-[12.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            상단에서 테스트 프리셋(예: app_checks 전체)을 선택해 실행하거나,
            관리자 권한 PowerShell에서{' '}
            <code className="font-mono-code rounded px-1 py-0.5 text-[11.5px]" style={{ backgroundColor: 'var(--bg-subtle)' }}>
              .\run.ps1 app -Dashboard
            </code>{' '}
            명령으로 실행하면 실시간 로그가 이곳에 스트리밍됩니다.
          </p>
        </div>
      </main>
    )
  }

  return (
    <main className="flex flex-1 flex-col overflow-hidden">
      {/* Sticky Control & Active Focus Bar */}
      <div
        className="flex h-10 shrink-0 items-center justify-between border-b px-4 text-[12px]"
        style={{
          backgroundColor: 'var(--bg-canvas)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="flex items-center gap-2 min-w-0">
          {activeCase ? (
            <>
              <StatusDot status="running" />
              <span className="font-medium shrink-0" style={{ color: 'var(--status-run)' }}>
                실행중
              </span>
              <span className="truncate" style={{ color: 'var(--text-secondary)' }}>
                {activeCase.category_title} ›{' '}
                {activeCase.tc_id && (
                  <span className="font-mono-code mr-1.5 opacity-80">[{activeCase.tc_id}]</span>
                )}
                <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                  {activeCase.title}
                </span>
              </span>
            </>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>
              {run.status === 'running' ? '테스트 수집 및 초기화 중...' : '테스트 실행 스트림'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => onToggleAutoFollow(!autoFollow)}
            className="inline-flex h-7 items-center gap-1.5 rounded border px-2 text-[11.5px] font-medium transition-colors cursor-pointer"
            style={{
              backgroundColor: autoFollow ? 'var(--accent-bg)' : 'var(--bg-surface)',
              borderColor: autoFollow ? 'var(--accent-primary)' : 'var(--border-subtle)',
              color: autoFollow ? 'var(--accent-primary)' : 'var(--text-secondary)',
            }}
            title="완료된 항목은 자동 접힘 처리하고 현재 실행 중인 테스트로 자동 포커스합니다"
          >
            <Crosshair className="h-3 w-3" />
            <span>{autoFollow ? '자동 포커스 ON' : '자동 포커스 OFF'}</span>
          </button>

          <button
            type="button"
            onClick={onCollapsePassed}
            className="inline-flex h-7 items-center gap-1 rounded border px-2 text-[11.5px] cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
            title="정상 완료 항목 모두 접기"
          >
            <Minimize2 className="h-3 w-3" />
            <span>완료 접기</span>
          </button>

          <button
            type="button"
            onClick={onExpandAll}
            className="inline-flex h-7 items-center gap-1 rounded border px-2 text-[11.5px] cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
            title="전체 항목 펼치기"
          >
            <Maximize2 className="h-3 w-3" />
            <span>전체 펼치기</span>
          </button>
        </div>
      </div>

      {/* Scrollable Hierarchical Accordion Stream */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {run.session_logs.length > 0 && (
          <div
            className="rounded-md border overflow-hidden"
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <div
              className="flex items-center justify-between border-b px-3 py-2 text-[12px] font-medium"
              style={{ borderColor: 'var(--border-subtle)', color: 'var(--text-secondary)' }}
            >
              <span>세션 초기화 / 공용 로그</span>
              <span className="font-mono-code text-[11px]">{run.session_logs.length} lines</span>
            </div>
            <LogConsole logs={run.session_logs} maxHeight="160px" />
          </div>
        )}

        {domains.map((dom) => (
          <section key={dom.domain} className="space-y-2.5">
            {/* 대분류 헤더 */}
            <div className="flex items-center justify-between px-0.5">
              <div className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4" style={{ color: 'var(--text-muted)' }} />
                <h2 className="text-[13px] font-semibold tracking-tight">{dom.title}</h2>
              </div>
              <div className="font-mono-code flex items-center gap-3 text-[11.5px]" style={{ color: 'var(--text-muted)' }}>
                <span style={{ color: 'var(--status-pass)' }}>PASS {dom.passed}</span>
                {dom.failed > 0 && <span style={{ color: 'var(--status-fail)' }}>FAIL {dom.failed}</span>}
                <span>TOTAL {dom.total}</span>
              </div>
            </div>

            {/* 중분류 아코디언 그룹 */}
            <div className="space-y-2">
              {dom.categories.map((cat) => (
                <CategoryAccordion
                  key={cat.key}
                  cat={cat}
                  statusFilter={statusFilter}
                  expanded={expandedCategories.has(cat.key)}
                  expandedCases={expandedCases}
                  onToggleCategory={() => onToggleCategory(cat.key)}
                  onToggleCase={onToggleCase}
                  registerCaseRef={registerCaseRef}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  )
}

function CategoryAccordion({
  cat,
  statusFilter,
  expanded,
  expandedCases,
  onToggleCategory,
  onToggleCase,
  registerCaseRef,
}: {
  cat: CategoryGroup
  statusFilter: 'all' | 'failed' | 'running' | 'passed'
  expanded: boolean
  expandedCases: Set<string>
  onToggleCategory: () => void
  onToggleCase: (nodeid: string) => void
  registerCaseRef: (nodeid: string, el: HTMLDivElement | null) => void
}) {
  const visibleCases = cat.cases.filter((tc) => {
    if (statusFilter === 'failed') return tc.status === 'failed' || tc.status === 'error'
    if (statusFilter === 'running') return tc.status === 'running'
    if (statusFilter === 'passed') return tc.status === 'passed'
    return true
  })

  if (visibleCases.length === 0) return null

  return (
    <div
      className="rounded-md border overflow-hidden transition-colors"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderColor: cat.status === 'running' ? 'var(--status-run-border)' : 'var(--border-subtle)',
      }}
    >
      {/* 중분류 헤더 */}
      <button
        type="button"
        onClick={onToggleCategory}
        className="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition-colors cursor-pointer"
        style={{
          backgroundColor: cat.status === 'running' ? 'var(--status-run-bg)' : 'transparent',
        }}
      >
        <div className="flex items-center gap-2 min-w-0">
          {expanded ? (
            <ChevronDown className="h-4 w-4 shrink-0" style={{ color: 'var(--text-muted)' }} />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0" style={{ color: 'var(--text-muted)' }} />
          )}
          <StatusDot status={cat.status} />
          <span className="truncate text-[13px] font-semibold">{cat.title}</span>
          <span className="font-mono-code text-[11px]" style={{ color: 'var(--text-muted)' }}>
            ({cat.passed + cat.failed + cat.skipped}/{cat.total})
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {cat.failed > 0 && (
            <span className="font-mono-code text-[11px] font-medium" style={{ color: 'var(--status-fail)' }}>
              오류 {cat.failed}건
            </span>
          )}
          <StatusBadge status={cat.status} duration={cat.duration > 0 ? cat.duration : null} />
        </div>
      </button>

      {/* 소분류(개별 테스트 케이스) 목록 */}
      {expanded && (
        <div className="divide-y border-t" style={{ borderColor: 'var(--border-subtle)' }}>
          {visibleCases.map((tc) => (
            <CaseAccordion
              key={tc.nodeid}
              tc={tc}
              expanded={expandedCases.has(tc.nodeid)}
              onToggle={() => onToggleCase(tc.nodeid)}
              registerRef={(el) => registerCaseRef(tc.nodeid, el)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function CaseAccordion({
  tc,
  expanded,
  onToggle,
  registerRef,
}: {
  tc: TestCaseState
  expanded: boolean
  onToggle: () => void
  registerRef: (el: HTMLDivElement | null) => void
}) {
  const isFailure = tc.status === 'failed' || tc.status === 'error'
  const isRunning = tc.status === 'running'

  return (
    <div
      ref={registerRef}
      style={{
        borderLeft: isFailure
          ? '3px solid var(--status-fail)'
          : isRunning
            ? '3px solid var(--status-run)'
            : '3px solid transparent',
        borderColor: 'var(--border-subtle)',
      }}
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3.5 py-2 text-left transition-colors cursor-pointer"
        style={{
          backgroundColor: isRunning ? 'var(--bg-subtle)' : 'transparent',
        }}
      >
        <div className="flex items-center gap-2 min-w-0 pr-3">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          )}
          <StatusDot status={tc.status} />
          {tc.tc_id && (
            <span
              className="font-mono-code shrink-0 rounded border px-1.5 py-0.5 text-[10.5px] font-medium"
              style={{
                backgroundColor: 'var(--bg-subtle)',
                borderColor: 'var(--border-strong)',
                color: 'var(--text-primary)',
              }}
            >
              {tc.tc_id}
            </span>
          )}
          {tc.subcategory_title && (
            <span
              className="shrink-0 rounded border px-1.5 py-0.5 text-[10.5px] font-medium"
              style={{
                backgroundColor: 'var(--bg-subtle)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-secondary)',
              }}
            >
              {tc.subcategory_title}
            </span>
          )}
          <span className="truncate text-[12.5px] font-medium">{tc.title}</span>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          {tc.logs.length > 0 && (
            <span className="font-mono-code text-[11px]" style={{ color: 'var(--text-muted)' }}>
              {tc.logs.length} lines
            </span>
          )}
          <StatusBadge status={tc.status} duration={tc.duration} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3 pt-1 space-y-2">
          {tc.error_message && (
            <div
              className="rounded border px-3 py-2 text-[12px]"
              style={{
                backgroundColor: 'var(--status-fail-bg)',
                borderColor: 'var(--status-fail-border)',
                color: 'var(--status-fail)',
              }}
            >
              <div className="font-semibold mb-0.5">실패 사유</div>
              <pre className="font-mono-code whitespace-pre-wrap text-[11.5px] leading-relaxed">
                {tc.error_message}
              </pre>
            </div>
          )}

          <LogConsole logs={tc.logs} isRunning={isRunning} />
        </div>
      )}
    </div>
  )
}

function LogConsole({
  logs,
  isRunning = false,
  maxHeight = '320px',
}: {
  logs: LogLine[]
  isRunning?: boolean
  maxHeight?: string
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (isRunning) {
      bottomRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' })
    }
  }, [logs.length, isRunning])

  if (logs.length === 0) {
    return (
      <div
        className="font-mono-code rounded border px-3 py-2 text-[11.5px]"
        style={{
          backgroundColor: 'var(--bg-terminal)',
          borderColor: 'var(--border-subtle)',
          color: 'var(--text-muted)',
        }}
      >
        {isRunning ? '실행 로그 수신 대기 중...' : '수집된 콘솔 로그가 없습니다.'}
      </div>
    )
  }

  return (
    <div
      className="font-mono-code overflow-y-auto rounded border p-2.5 text-[11.5px] leading-[1.55]"
      style={{
        maxHeight,
        backgroundColor: 'var(--bg-terminal)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {logs.map((line, idx) => {
        const lineColor =
          line.level === 'error'
            ? 'var(--status-fail)'
            : line.level === 'success'
              ? 'var(--status-pass)'
              : line.level === 'warn'
                ? 'var(--status-warn)'
                : line.level === 'step'
                  ? 'var(--accent-primary)'
                  : 'var(--text-primary)'

        return (
          <div key={`${line.seq}-${idx}`} className="flex items-start gap-2.5 hover:bg-black/5 dark:hover:bg-white/5 px-1 rounded">
            <span className="w-7 shrink-0 select-none text-right text-[10.5px]" style={{ color: 'var(--text-muted)' }}>
              {idx + 1}
            </span>
            <span className="shrink-0 select-none text-[10.5px]" style={{ color: 'var(--text-muted)' }}>
              {line.timestamp.slice(11, 19)}
            </span>
            <span className="whitespace-pre-wrap break-all" style={{ color: lineColor }}>
              {line.text}
            </span>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}
