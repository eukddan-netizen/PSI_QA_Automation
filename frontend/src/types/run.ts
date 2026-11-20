export type TestStatus = 'pending' | 'running' | 'passed' | 'failed' | 'skipped' | 'error' | 'warning'
export type RunStatus = 'idle' | 'running' | 'completed' | 'failed' | 'stopped'
export type LogStream = 'stdout' | 'stderr' | 'system'
export type LogLevel = 'info' | 'step' | 'warn' | 'error' | 'success'

export interface EnvironmentInfo {
  os: string
  hostname: string
  ip: string
  python_version: string
  is_admin: boolean
}

export interface LogLine {
  seq: number
  timestamp: string
  stream: LogStream
  level: LogLevel
  stage?: string | null
  text: string
  nodeid?: string | null
}

export interface TestCaseState {
  nodeid: string
  tc_id?: string
  id: string
  title: string
  docstring: string
  domain: string
  domain_title: string
  category_id: string
  category_title: string
  subcategory_id?: string | null
  subcategory_title?: string | null
  markers: string[]
  status: TestStatus
  duration?: number | null
  started_at?: string | null
  finished_at?: string | null
  summary: string
  error_message: string
  logs: LogLine[]
}

export interface RunSummary {
  total: number
  completed: number
  passed: number
  failed: number
  skipped: number
  running: number
  pending: number
  pass_rate: number
  duration_sec: number
}

export interface RunState {
  run_id: string
  title: string
  target: string
  status: RunStatus
  started_at: string
  finished_at?: string | null
  environment: EnvironmentInfo
  summary: RunSummary
  cases: TestCaseState[]
  session_logs: LogLine[]
  active_nodeid?: string | null
}

export interface RunListItem {
  run_id: string
  title: string
  target: string
  status: RunStatus
  started_at: string
  finished_at?: string | null
  summary: RunSummary
}

export interface CatalogPreset {
  id: string
  label: string
  domain: string
  markers?: string | null
  paths: string[]
  description: string
}

export interface StartRunPayload {
  target: string
  markers?: string | null
  paths?: string[]
  nodeids?: string[]
  keyword?: string | null
  title: string
  run_id?: string | null
  accumulate?: boolean
}

export interface RunnerStatus {
  is_running: boolean
  active_run_id?: string | null
  is_admin: boolean
}

export interface CategoryGroup {
  key: string
  domain: string
  categoryId: string
  title: string
  status: TestStatus
  total: number
  passed: number
  failed: number
  skipped: number
  running: number
  pending: number
  duration: number
  cases: TestCaseState[]
}

export interface DomainGroup {
  domain: string
  title: string
  status: TestStatus
  total: number
  passed: number
  failed: number
  skipped: number
  running: number
  pending: number
  categories: CategoryGroup[]
}

export function deriveAggregateStatus(
  items: { status: TestStatus }[],
  isRunActive = true,
): TestStatus {
  if (items.some((i) => i.status === 'running')) return 'running'
  if (items.some((i) => i.status === 'failed' || i.status === 'error')) return 'failed'
  if (items.length > 0 && items.every((i) => i.status === 'skipped')) return 'skipped'
  if (items.length > 0 && items.every((i) => i.status === 'passed' || i.status === 'skipped')) return 'passed'
  if (items.some((i) => i.status === 'passed')) return isRunActive ? 'running' : 'passed'
  return 'pending'
}

export function mergeCatalogWithRunCases(
  catalogCases: TestCaseState[],
  runCases: TestCaseState[],
): TestCaseState[] {
  if (catalogCases.length === 0) return runCases
  if (runCases.length === 0) return catalogCases

  const runByNodeId = new Map<string, TestCaseState>()
  for (const rc of runCases) {
    runByNodeId.set(rc.nodeid, rc)
  }

  const seen = new Set<string>()
  const merged: TestCaseState[] = []

  for (const cc of catalogCases) {
    const matched = runByNodeId.get(cc.nodeid)
    merged.push(matched ?? cc)
    seen.add(cc.nodeid)
  }

  for (const rc of runCases) {
    if (!seen.has(rc.nodeid)) {
      merged.push(rc)
    }
  }

  return merged
}

export function buildHierarchyTree(cases: TestCaseState[], isRunActive = true): DomainGroup[] {
  const domainMap = new Map<string, { title: string; catMap: Map<string, CategoryGroup> }>()

  for (const c of cases) {
    let dom = domainMap.get(c.domain)
    if (!dom) {
      dom = { title: c.domain_title, catMap: new Map() }
      domainMap.set(c.domain, dom)
    }

    const catKey = `${c.domain}::${c.category_id}`
    let cat = dom.catMap.get(catKey)
    if (!cat) {
      cat = {
        key: catKey,
        domain: c.domain,
        categoryId: c.category_id,
        title: c.category_title,
        status: 'pending',
        total: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        running: 0,
        pending: 0,
        duration: 0,
        cases: [],
      }
      dom.catMap.set(catKey, cat)
    }

    cat.cases.push(c)
    cat.total += 1
    if (c.status === 'passed') cat.passed += 1
    else if (c.status === 'failed' || c.status === 'error') cat.failed += 1
    else if (c.status === 'skipped') cat.skipped += 1
    else if (c.status === 'running') cat.running += 1
    else cat.pending += 1
    cat.duration += c.duration ?? 0
  }

  const result: DomainGroup[] = []
  for (const [domain, domVal] of domainMap.entries()) {
    const categories = Array.from(domVal.catMap.values()).map((cat) => ({
      ...cat,
      status: deriveAggregateStatus(cat.cases, isRunActive),
    }))
    const allCases = categories.flatMap((cat) => cat.cases)
    result.push({
      domain,
      title: domVal.title,
      status: deriveAggregateStatus(categories, isRunActive),
      total: allCases.length,
      passed: categories.reduce((acc, cat) => acc + cat.passed, 0),
      failed: categories.reduce((acc, cat) => acc + cat.failed, 0),
      skipped: categories.reduce((acc, cat) => acc + cat.skipped, 0),
      running: categories.reduce((acc, cat) => acc + cat.running, 0),
      pending: categories.reduce((acc, cat) => acc + cat.pending, 0),
      categories,
    })
  }

  return result
}

export function parseTimestampMs(ts?: string | null): number | null {
  if (!ts) return null
  const normalized = ts.includes('T') ? ts : ts.replace(' ', 'T')
  const ms = Date.parse(normalized)
  return Number.isFinite(ms) ? ms : null
}

export function getElapsedSeconds(startedAt?: string | null, nowMs: number = Date.now()): number | null {
  const startMs = parseTimestampMs(startedAt)
  if (startMs === null) return null
  return Math.max(0, (nowMs - startMs) / 1000)
}

export function formatElapsedDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0초'
  const totalSeconds = Math.floor(seconds)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const secs = totalSeconds % 60
  if (hours > 0) {
    return `${hours}시간 ${String(minutes).padStart(2, '0')}분 ${String(secs).padStart(2, '0')}초`
  }
  if (minutes > 0) {
    return `${minutes}분 ${String(secs).padStart(2, '0')}초`
  }
  return `${secs}초`
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0.00초'
  if (seconds < 60) {
    return `${seconds.toFixed(2)}초`
  }
  const totalSeconds = Math.round(seconds)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const secs = totalSeconds % 60
  if (hours > 0) {
    return `${hours}시간 ${String(minutes).padStart(2, '0')}분 ${String(secs).padStart(2, '0')}초`
  }
  return `${minutes}분 ${String(secs).padStart(2, '0')}초`
}
