import { Check, Loader2, Minus, X, AlertTriangle, Clock } from 'lucide-react'
import { formatDuration, type TestStatus } from '../types/run'

const STATUS_META: Record<
  TestStatus,
  { label: string; color: string; bg: string; border: string }
> = {
  passed: {
    label: 'PASS',
    color: 'var(--status-pass)',
    bg: 'var(--status-pass-bg)',
    border: 'var(--status-pass-border)',
  },
  failed: {
    label: 'FAIL',
    color: 'var(--status-fail)',
    bg: 'var(--status-fail-bg)',
    border: 'var(--status-fail-border)',
  },
  error: {
    label: 'ERROR',
    color: 'var(--status-fail)',
    bg: 'var(--status-fail-bg)',
    border: 'var(--status-fail-border)',
  },
  running: {
    label: 'RUN',
    color: 'var(--status-run)',
    bg: 'var(--status-run-bg)',
    border: 'var(--status-run-border)',
  },
  skipped: {
    label: 'SKIP',
    color: 'var(--status-skip)',
    bg: 'var(--status-skip-bg)',
    border: 'var(--status-skip-border)',
  },
  warning: {
    label: 'WARN',
    color: 'var(--status-warn)',
    bg: 'var(--status-warn-bg)',
    border: 'var(--status-warn-border)',
  },
  pending: {
    label: 'WAIT',
    color: 'var(--text-muted)',
    bg: 'var(--bg-subtle)',
    border: 'var(--border-subtle)',
  },
}

export function StatusDot({ status }: { status: TestStatus }) {
  if (status === 'running') {
    return (
      <span className="relative flex h-2.5 w-2.5 shrink-0 items-center justify-center">
        <span
          className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
          style={{ backgroundColor: 'var(--status-run)' }}
        />
        <span
          className="relative inline-flex h-2 w-2 rounded-full"
          style={{ backgroundColor: 'var(--status-run)' }}
        />
      </span>
    )
  }

  const color = STATUS_META[status]?.color ?? 'var(--text-muted)'
  return (
    <span
      className="inline-block h-2 w-2 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
  )
}

export function StatusBadge({
  status,
  duration,
}: {
  status: TestStatus
  duration?: number | null
}) {
  const meta = STATUS_META[status] ?? STATUS_META.pending

  return (
    <span
      className="font-mono-code inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium leading-none border"
      style={{
        color: meta.color,
        backgroundColor: meta.bg,
        borderColor: meta.border,
      }}
    >
      {status === 'passed' && <Check className="h-3 w-3 stroke-[2.5]" />}
      {(status === 'failed' || status === 'error') && <X className="h-3 w-3 stroke-[2.5]" />}
      {status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
      {status === 'skipped' && <Minus className="h-3 w-3" />}
      {status === 'warning' && <AlertTriangle className="h-3 w-3" />}
      {status === 'pending' && <Clock className="h-3 w-3" />}
      <span>{meta.label}</span>
      {duration != null && status !== 'running' && status !== 'pending' && (
        <span className="opacity-75">· {formatDuration(duration)}</span>
      )}
    </span>
  )
}
