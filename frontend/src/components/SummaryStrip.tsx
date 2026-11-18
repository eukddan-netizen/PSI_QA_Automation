import { formatDuration, type RunState } from '../types/run'

export function SummaryStrip({ run }: { run: RunState | null }) {
  if (!run) {
    return (
      <div
        className="flex h-10 shrink-0 items-center justify-between border-b px-4 text-[12px]"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border-subtle)',
          color: 'var(--text-muted)',
        }}
      >
        <span>실행 중인 테스트가 없습니다. 상단에서 대상을 선택해 실행하거나 PowerShell에서 `pytest --dashboard`를 실행하세요.</span>
      </div>
    )
  }

  const { summary } = run
  const pct = summary.total > 0 ? Math.round((summary.completed / summary.total) * 100) : 0
  const remaining = Math.max(0, summary.total - summary.completed)

  return (
    <div
      className="shrink-0 border-b"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      <div className="flex h-10 items-center justify-between px-4 text-[12px]">
        <div className="flex items-center gap-5">
          <Metric label="전체" value={`${summary.total}`} />
          <Metric label="완료" value={`${summary.completed} (${pct}%)`} />
          <Metric
            label="잔여"
            value={`${remaining}`}
            color={remaining > 0 ? 'var(--text-primary)' : 'var(--text-muted)'}
          />
          <Metric label="정상" value={`${summary.passed}`} color="var(--status-pass)" />
          <Metric
            label="오류"
            value={`${summary.failed}`}
            color={summary.failed > 0 ? 'var(--status-fail)' : 'var(--text-muted)'}
          />
          <Metric label="제외" value={`${summary.skipped}`} color="var(--status-skip)" />
          <Metric label="정상률" value={`${summary.pass_rate.toFixed(1)}%`} />
          <Metric label="누적시간" value={formatDuration(summary.duration_sec)} />
        </div>

        <div className="flex items-center gap-3 text-[11px]" style={{ color: 'var(--text-muted)' }}>
          {run.environment.hostname && (
            <span className="font-mono-code">
              {run.environment.hostname}
              {run.environment.ip ? ` (${run.environment.ip})` : ''}
            </span>
          )}
          <span className="font-mono-code">ID: {run.run_id}</span>
        </div>
      </div>

      {/* Hairline progress bar */}
      <div className="h-[2px] w-full" style={{ backgroundColor: 'var(--bg-subtle)' }}>
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${pct}%`,
            backgroundColor:
              summary.failed > 0
                ? 'var(--status-fail)'
                : run.status === 'running'
                  ? 'var(--status-run)'
                  : 'var(--status-pass)',
          }}
        />
      </div>
    </div>
  )
}

function Metric({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span
        className="font-mono-code font-semibold"
        style={{ color: color ?? 'var(--text-primary)' }}
      >
        {value}
      </span>
    </div>
  )
}
