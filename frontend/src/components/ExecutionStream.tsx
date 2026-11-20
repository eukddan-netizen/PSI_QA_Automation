import { useEffect, useRef, useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Crosshair,
  FolderOpen,
  Minimize2,
  Maximize2,
  Monitor,
  Play,
  RotateCw,
} from 'lucide-react'
import {
  formatElapsedDuration,
  getElapsedSeconds,
  type CategoryGroup,
  type DomainGroup,
  type LogLine,
  type RunState,
  type TestCaseState,
} from '../types/run'
import { StatusBadge, StatusDot } from './StatusBadge'

interface ExecutionStreamProps {
  run: RunState | null
  historyCount?: number
  domains: DomainGroup[]
  statusFilter: 'all' | 'failed' | 'running' | 'passed'
  autoFollow: boolean
  isRunning: boolean
  nowMs?: number
  expandedCategories: Set<string>
  expandedCases: Set<string>
  onToggleAutoFollow: (val: boolean) => void
  onToggleCategory: (catKey: string) => void
  onToggleCase: (nodeid: string) => void
  onRunSingleCase: (tc: TestCaseState) => Promise<void> | void
  onExpandAll: () => void
  onCollapsePassed: () => void
  registerCaseRef: (nodeid: string, el: HTMLDivElement | null) => void
}

export function ExecutionStream({
  run,
  historyCount = 0,
  domains,
  statusFilter,
  autoFollow,
  isRunning,
  nowMs,
  expandedCategories,
  expandedCases,
  onToggleAutoFollow,
  onToggleCategory,
  onToggleCase,
  onRunSingleCase,
  onExpandAll,
  onCollapsePassed,
  registerCaseRef,
}: ExecutionStreamProps) {
  const activeCase = run?.cases.find((c) => c.nodeid === run.active_nodeid) ?? null
  const activeElapsed =
    activeCase && activeCase.status === 'running'
      ? getElapsedSeconds(activeCase.started_at, nowMs)
      : null
  const [launchingNodeId, setLaunchingNodeId] = useState<string | null>(null)

  const handleRunCase = async (tc: TestCaseState) => {
    if (isRunning || launchingNodeId) return
    setLaunchingNodeId(tc.nodeid)
    try {
      await onRunSingleCase(tc)
    } finally {
      setLaunchingNodeId(null)
    }
  }

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
          <Monitor className="mx-auto mb-3 h-7 w-7" style={{ color: 'var(--text-muted)' }} />
          <h2 className="text-[14px] font-semibold">QA 자동화 실시간 로그 대기 중</h2>
          <p className="mt-1.5 text-[12.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {historyCount > 0
              ? '좌측 테스트 트리에서 개별 항목의 실행 아이콘(▶)을 눌러 바로 테스트하거나, 우측 상단에서 대상을 체크해 실행 및 이전 이력을 불러올 수 있습니다.'
              : '좌측 테스트 트리에서 개별 항목의 실행 아이콘(▶)을 누르거나, 우측 상단에서 실행 대상을 체크해 테스트를 시작하면 실시간 로그가 이곳에 스트리밍됩니다.'}
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
          backgroundColor: 'var(--bg-sticky-bar)',
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
              {activeElapsed != null && (
                <span
                  className="font-mono-code tabular-nums shrink-0 rounded border px-1.5 py-0.5 text-[11px] font-medium"
                  style={{
                    color: 'var(--status-run)',
                    backgroundColor: 'var(--status-run-bg)',
                    borderColor: 'var(--status-run-border)',
                  }}
                >
                  {formatElapsedDuration(activeElapsed)}
                </span>
              )}
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

        {domains.map((dom) => {
          const remaining = Math.max(0, dom.total - (dom.passed + dom.failed + dom.skipped))
          return (
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
                  {dom.skipped > 0 && <span style={{ color: 'var(--status-skip)' }}>SKIP {dom.skipped}</span>}
                  <span
                    title="잔여 항목 수"
                    style={{ color: remaining > 0 ? 'var(--text-secondary)' : 'var(--text-muted)' }}
                  >
                    REMAIN {remaining}
                  </span>
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
                    isRunning={isRunning}
                    nowMs={nowMs}
                    launchingNodeId={launchingNodeId}
                    onToggleCategory={() => onToggleCategory(cat.key)}
                    onToggleCase={onToggleCase}
                    onRunSingleCase={handleRunCase}
                    registerCaseRef={registerCaseRef}
                  />
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </main>
  )
}

function CategoryAccordion({
  cat,
  statusFilter,
  expanded,
  expandedCases,
  isRunning,
  nowMs,
  launchingNodeId,
  onToggleCategory,
  onToggleCase,
  onRunSingleCase,
  registerCaseRef,
}: {
  cat: CategoryGroup
  statusFilter: 'all' | 'failed' | 'running' | 'passed'
  expanded: boolean
  expandedCases: Set<string>
  isRunning: boolean
  nowMs?: number
  launchingNodeId: string | null
  onToggleCategory: () => void
  onToggleCase: (nodeid: string) => void
  onRunSingleCase: (tc: TestCaseState) => void
  registerCaseRef: (nodeid: string, el: HTMLDivElement | null) => void
}) {
  const visibleCases = cat.cases.filter((tc) => {
    if (statusFilter === 'failed') return tc.status === 'failed' || tc.status === 'error'
    if (statusFilter === 'running') return tc.status === 'running'
    if (statusFilter === 'passed') return tc.status === 'passed'
    return true
  })

  if (visibleCases.length === 0) return null

  const runningExtraSec =
    cat.status === 'running'
      ? cat.cases.reduce((acc, tc) => {
          if (tc.status !== 'running') return acc
          return acc + (getElapsedSeconds(tc.started_at, nowMs) ?? 0)
        }, 0)
      : 0
  const catBadgeDuration =
    cat.status === 'running'
      ? cat.duration + runningExtraSec
      : cat.duration > 0
        ? cat.duration
        : null

  return (
    <div
      className="rounded-md border overflow-hidden transition-colors"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderColor: cat.status === 'running' ? 'var(--status-run-border)' : 'var(--border-subtle)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      {/* 중분류 헤더 */}
      <button
        type="button"
        onClick={onToggleCategory}
        className="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition-colors cursor-pointer"
        style={{
          backgroundColor: cat.status === 'running' ? 'var(--status-run-bg)' : 'var(--bg-category-header)',
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
          <StatusBadge status={cat.status} duration={catBadgeDuration} />
        </div>
      </button>

      {/* 소분류(개별 테스트 케이스) 목록 */}
      {expanded && (
        <div className="divide-y border-t" style={{ borderColor: 'var(--border-row)' }}>
          {visibleCases.map((tc) => (
            <CaseAccordion
              key={tc.nodeid}
              tc={tc}
              expanded={expandedCases.has(tc.nodeid)}
              isRunnerBusy={isRunning || launchingNodeId !== null}
              isLaunchingThis={launchingNodeId === tc.nodeid}
              nowMs={nowMs}
              onToggle={() => onToggleCase(tc.nodeid)}
              onRunSingle={() => onRunSingleCase(tc)}
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
  isRunnerBusy,
  isLaunchingThis,
  nowMs,
  onToggle,
  onRunSingle,
  registerRef,
}: {
  tc: TestCaseState
  expanded: boolean
  isRunnerBusy: boolean
  isLaunchingThis: boolean
  nowMs?: number
  onToggle: () => void
  onRunSingle: () => void
  registerRef: (el: HTMLDivElement | null) => void
}) {
  const isFailure = tc.status === 'failed' || tc.status === 'error'
  const isRunning = tc.status === 'running'
  const isPending = tc.status === 'pending'
  const liveElapsed = isRunning ? getElapsedSeconds(tc.started_at, nowMs) : null

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
      <div
        className="flex w-full items-center justify-between transition-colors hover:bg-[var(--bg-hover)]"
        style={{
          backgroundColor: isRunning ? 'var(--bg-subtle)' : 'transparent',
        }}
      >
        <button
          type="button"
          onClick={onToggle}
          className="flex min-w-0 flex-1 items-center gap-2 px-3.5 py-2 text-left cursor-pointer"
        >
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
        </button>

        <div className="flex items-center gap-2 pr-3 shrink-0">
          {tc.logs.length > 0 && (
            <span className="font-mono-code text-[11px]" style={{ color: 'var(--text-muted)' }}>
              {tc.logs.length} lines
            </span>
          )}
          <StatusBadge status={tc.status} duration={isRunning ? liveElapsed : tc.duration} />
          <button
            type="button"
            disabled={isRunnerBusy}
            onClick={(e) => {
              e.stopPropagation()
              onRunSingle()
            }}
            title={
              isRunnerBusy
                ? '다른 테스트가 실행 중입니다'
                : isPending
                  ? '이 항목만 단건 실행'
                  : '이 항목만 단건 재실행'
            }
            aria-label={`${tc.tc_id || tc.title} 단건 실행`}
            className="inline-flex h-6 items-center gap-1 rounded border px-1.5 text-[11px] font-medium transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-35 cursor-pointer"
            style={{
              backgroundColor: isFailure ? 'var(--status-fail-bg)' : 'var(--bg-subtle)',
              borderColor: isFailure ? 'var(--status-fail-border)' : 'var(--border-subtle)',
              color: isFailure ? 'var(--status-fail)' : 'var(--text-secondary)',
            }}
          >
            {isPending ? (
              <Play className="h-2.5 w-2.5 fill-current" />
            ) : (
              <RotateCw className={`h-2.5 w-2.5 ${isLaunchingThis ? 'animate-spin' : ''}`} />
            )}
            <span>{isPending ? '실행' : '재실행'}</span>
          </button>
        </div>
      </div>

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
