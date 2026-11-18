import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, ListChecks, Minus } from 'lucide-react'
import type { CatalogPreset, StartRunPayload } from '../types/run'

interface TargetSelectorProps {
  presets: CatalogPreset[]
  disabled?: boolean
  selectedIds: Set<string>
  useAllTarget: boolean
  onChangeSelection: (nextIds: Set<string>, nextUseAll: boolean) => void
}

function shortLabel(label: string): string {
  const idx = label.indexOf(' · ')
  return idx >= 0 ? label.slice(0, idx) : label
}

export function buildRunPayload(
  presets: CatalogPreset[],
  selectedIds: Set<string>,
  useAllTarget: boolean,
): StartRunPayload | null {
  const allPreset = presets.find((p) => p.id === 'all')
  if (useAllTarget && allPreset) {
    return {
      target: allPreset.id,
      markers: allPreset.markers ?? null,
      paths: allPreset.paths ?? [],
      title: allPreset.label,
    }
  }

  const appChildren = presets.filter((p) => p.domain === 'app_checks' && p.id !== 'app_all')
  const secChildren = presets.filter((p) => p.domain === 'security_checks')

  const selectedApp = appChildren.filter((p) => selectedIds.has(p.id))
  const selectedSec = secChildren.filter((p) => selectedIds.has(p.id))
  const selectedAll = [...selectedApp, ...selectedSec]

  if (selectedAll.length === 0) {
    return null
  }

  const allAppSelected = appChildren.length > 0 && selectedApp.length === appChildren.length

  // Optimize pure app_checks full selection to match existing app_all preset
  if (allAppSelected && selectedSec.length === 0) {
    const appAllPreset = presets.find((p) => p.id === 'app_all')
    return {
      target: 'app_all',
      markers: appAllPreset?.markers ?? 'app_check',
      paths: appAllPreset?.paths ?? [],
      title: appAllPreset?.label ?? 'app_checks 전체',
    }
  }

  const markerParts: string[] = []
  if (allAppSelected) {
    markerParts.push('app_check')
  } else {
    for (const p of selectedApp) {
      if (p.markers) markerParts.push(p.markers)
    }
  }
  for (const p of selectedSec) {
    if (p.markers) markerParts.push(p.markers)
  }

  const markers =
    markerParts.length === 0
      ? null
      : markerParts.length === 1
        ? markerParts[0]
        : markerParts.map((m) => (m.includes(' or ') ? `(${m})` : m)).join(' or ')

  let title: string
  if (selectedAll.length === 1) {
    title = selectedAll[0].label
  } else if (allAppSelected && selectedSec.length > 0) {
    const secNames = selectedSec.map((p) => shortLabel(p.label)).join(', ')
    title = `app_checks 전체 + ${secNames}`
  } else if (selectedAll.length <= 2) {
    title = selectedAll.map((p) => shortLabel(p.label)).join(' + ')
  } else {
    title = `${shortLabel(selectedAll[0].label)} 외 ${selectedAll.length - 1}건`
  }

  return {
    target: selectedAll.map((p) => p.id).join(','),
    markers,
    paths: [],
    title,
  }
}

export function TargetSelector({
  presets,
  disabled = false,
  selectedIds,
  useAllTarget,
  onChangeSelection,
}: TargetSelectorProps) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  const appChildren = useMemo(
    () => presets.filter((p) => p.domain === 'app_checks' && p.id !== 'app_all'),
    [presets],
  )
  const secChildren = useMemo(
    () => presets.filter((p) => p.domain === 'security_checks'),
    [presets],
  )
  const allPreset = useMemo(() => presets.find((p) => p.id === 'all'), [presets])

  useEffect(() => {
    if (disabled) setOpen(false)
  }, [disabled])

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

  const appSelectedCount = appChildren.filter((p) => selectedIds.has(p.id)).length
  const appAllChecked = appChildren.length > 0 && appSelectedCount === appChildren.length
  const appIndeterminate = appSelectedCount > 0 && appSelectedCount < appChildren.length

  const secSelectedCount = secChildren.filter((p) => selectedIds.has(p.id)).length
  const secAllChecked = secChildren.length > 0 && secSelectedCount === secChildren.length
  const secIndeterminate = secSelectedCount > 0 && secSelectedCount < secChildren.length

  const totalSelectedCount = appSelectedCount + secSelectedCount

  const summaryText = useMemo(() => {
    if (useAllTarget && allPreset) return allPreset.label
    if (totalSelectedCount === 0) return '테스트 대상 선택 (0)'
    if (appAllChecked && secSelectedCount === 0) return `app_checks 전체 (${appChildren.length})`
    const first = [...appChildren, ...secChildren].find((p) => selectedIds.has(p.id))
    if (totalSelectedCount === 1 && first) return first.label
    return `${first ? shortLabel(first.label) : '선택됨'} 외 ${totalSelectedCount - 1}건`
  }, [
    useAllTarget,
    allPreset,
    totalSelectedCount,
    appAllChecked,
    secSelectedCount,
    appChildren,
    secChildren,
    selectedIds,
  ])

  const toggleGroup = (children: CatalogPreset[], allChecked: boolean) => {
    const next = new Set(selectedIds)
    if (allChecked) {
      children.forEach((c) => next.delete(c.id))
    } else {
      children.forEach((c) => next.add(c.id))
    }
    onChangeSelection(next, false)
  }

  const toggleItem = (id: string) => {
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onChangeSelection(next, false)
  }

  const toggleAllTarget = () => {
    if (useAllTarget) {
      onChangeSelection(new Set(), false)
    } else {
      const next = new Set<string>()
      appChildren.forEach((c) => next.add(c.id))
      secChildren.forEach((c) => next.add(c.id))
      onChangeSelection(next, true)
    }
  }

  const selectAppOnly = () => {
    const next = new Set<string>()
    appChildren.forEach((c) => next.add(c.id))
    onChangeSelection(next, false)
  }

  const clearAll = () => {
    onChangeSelection(new Set(), false)
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        disabled={disabled || presets.length === 0}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="테스트 실행 대상 선택"
        className="inline-flex h-8 min-w-[215px] max-w-[270px] items-center justify-between gap-2 rounded border px-2.5 text-[12px] outline-none transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
        style={{
          backgroundColor: 'var(--bg-header-control)',
          borderColor: open ? 'var(--accent-primary)' : 'var(--border-header)',
          color: 'var(--text-header)',
        }}
      >
        <span className="flex items-center gap-1.5 truncate">
          <ListChecks className="h-3.5 w-3.5 shrink-0" style={{ color: 'var(--text-header-muted)' }} />
          <span className="truncate">{summaryText}</span>
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          style={{ color: 'var(--text-header-muted)' }}
        />
      </button>

      {open && (
        <div
          className="absolute right-0 top-full z-50 mt-1.5 w-[350px] rounded-md border shadow-xl select-none"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border-strong)',
            color: 'var(--text-primary)',
          }}
        >
          {/* Popover Header */}
          <div
            className="flex items-center justify-between border-b px-3 py-2 text-[11.5px]"
            style={{
              backgroundColor: 'var(--bg-category-header)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
              실행 대상 선택{' '}
              <span className="font-mono-code font-normal" style={{ color: 'var(--text-muted)' }}>
                ({useAllTarget ? '전체' : `${totalSelectedCount}개`})
              </span>
            </span>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={selectAppOnly}
                className="rounded border px-1.5 py-0.5 text-[11px] hover:opacity-80 cursor-pointer"
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  borderColor: 'var(--border-subtle)',
                  color: 'var(--text-secondary)',
                }}
              >
                app 전체
              </button>
              <button
                type="button"
                onClick={clearAll}
                className="rounded border px-1.5 py-0.5 text-[11px] hover:opacity-80 cursor-pointer"
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  borderColor: 'var(--border-subtle)',
                  color: 'var(--text-muted)',
                }}
              >
                선택 해제
              </button>
            </div>
          </div>

          {/* Hierarchical Checkbox Tree */}
          <div className="max-h-[380px] overflow-y-auto p-2 space-y-2.5 text-[12px]">
            {/* Parent Group 1: app_checks */}
            {appChildren.length > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => toggleGroup(appChildren, appAllChecked)}
                  className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left font-semibold transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <CheckboxBox checked={appAllChecked} indeterminate={appIndeterminate} />
                    <span className="truncate">app_checks (프로그램 기능 점검)</span>
                  </span>
                  <span className="font-mono-code ml-2 shrink-0 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    {appSelectedCount}/{appChildren.length}
                  </span>
                </button>

                {/* Indented Children */}
                <div
                  className="ml-3.5 mt-0.5 space-y-0.5 border-l pl-3"
                  style={{ borderColor: 'var(--border-subtle)' }}
                >
                  {appChildren.map((item) => {
                    const checked = selectedIds.has(item.id)
                    return (
                      <button
                        key={item.id}
                        type="button"
                        title={item.description}
                        onClick={() => toggleItem(item.id)}
                        className="flex w-full items-center gap-2 rounded px-2 py-1 text-left transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
                        style={{ color: checked ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                      >
                        <CheckboxBox checked={checked} />
                        <span className="truncate text-[11.5px]">{item.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Parent Group 2: security_checks */}
            {secChildren.length > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => toggleGroup(secChildren, secAllChecked)}
                  className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left font-semibold transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <CheckboxBox checked={secAllChecked} indeterminate={secIndeterminate} />
                    <span className="truncate">security_checks (보안점검 항목)</span>
                  </span>
                  <span className="font-mono-code ml-2 shrink-0 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    {secSelectedCount}/{secChildren.length}
                  </span>
                </button>

                {/* Indented Children */}
                <div
                  className="ml-3.5 mt-0.5 space-y-0.5 border-l pl-3"
                  style={{ borderColor: 'var(--border-subtle)' }}
                >
                  {secChildren.map((item) => {
                    const checked = selectedIds.has(item.id)
                    return (
                      <button
                        key={item.id}
                        type="button"
                        title={item.description}
                        onClick={() => toggleItem(item.id)}
                        className="flex w-full items-center gap-2 rounded px-2 py-1 text-left transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
                        style={{ color: checked ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                      >
                        <CheckboxBox checked={checked} />
                        <span className="truncate text-[11.5px]">{item.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Full Suite Option */}
            {allPreset && (
              <div className="border-t pt-2" style={{ borderColor: 'var(--border-subtle)' }}>
                <button
                  type="button"
                  title={allPreset.description}
                  onClick={toggleAllTarget}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left transition-colors hover:bg-[var(--bg-hover)] cursor-pointer"
                >
                  <CheckboxBox checked={useAllTarget} />
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-[12px]">{allPreset.label}</div>
                    <div className="truncate text-[10.5px]" style={{ color: 'var(--text-muted)' }}>
                      {allPreset.description}
                    </div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function CheckboxBox({
  checked,
  indeterminate = false,
}: {
  checked: boolean
  indeterminate?: boolean
}) {
  return (
    <span
      className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-[3px] border transition-colors"
      style={{
        backgroundColor: checked
          ? 'var(--accent-primary)'
          : indeterminate
            ? 'var(--accent-bg)'
            : 'transparent',
        borderColor: checked || indeterminate ? 'var(--accent-primary)' : 'var(--border-strong)',
        color: checked ? '#ffffff' : 'var(--accent-primary)',
      }}
    >
      {checked ? (
        <Check className="h-2.5 w-2.5 stroke-[3]" />
      ) : indeterminate ? (
        <Minus className="h-2.5 w-2.5 stroke-[3]" />
      ) : null}
    </span>
  )
}
