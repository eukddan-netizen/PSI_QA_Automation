import { useCallback, useEffect, useRef, useState } from 'react'
import type { CategoryGroup, RunState, TestStatus } from '../types/run'

interface AutoFocusState {
  autoFollow: boolean
  setAutoFollow: (val: boolean) => void
  expandedCategories: Set<string>
  expandedCases: Set<string>
  toggleCategory: (catKey: string) => void
  toggleCase: (nodeid: string) => void
  focusCase: (catKey: string, nodeid: string) => void
  expandAll: () => void
  collapsePassed: () => void
  registerCaseRef: (nodeid: string, el: HTMLDivElement | null) => void
}

/**
 * Smart Accordion & Auto-Focus Controller:
 * - Expands the active category and running case automatically.
 * - Auto-collapses passed/skipped cases ~450ms after completion so only a concise badge remains.
 * - Keeps failed/error cases pinned open so issues are never hidden.
 * - Auto-collapses a category once all its cases finish without failures.
 */
export function useAutoFocus(
  run: RunState | null,
  categories: CategoryGroup[],
  runBatchSeq = 0,
): AutoFocusState {
  const [autoFollow, setAutoFollow] = useState(true)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => new Set())
  const [expandedCases, setExpandedCases] = useState<Set<string>>(() => new Set())

  const prevStatusesRef = useRef<Map<string, TestStatus>>(new Map())
  const prevCatStatusesRef = useRef<Map<string, TestStatus>>(new Map())
  const caseRefs = useRef<Map<string, HTMLDivElement>>(new Map())
  const lastRunIdRef = useRef<string | null>(null)
  const lastBatchSeqRef = useRef<number>(runBatchSeq)
  const prevRunStatusRef = useRef<RunState['status'] | null>(null)
  const collapseTimersRef = useRef<number[]>([])

  const registerCaseRef = useCallback((nodeid: string, el: HTMLDivElement | null) => {
    if (el) caseRefs.current.set(nodeid, el)
    else caseRefs.current.delete(nodeid)
  }, [])

  // Reset state cleanly when clearing view, switching runs, or starting a new batch on the same run
  useEffect(() => {
    if (!run) {
      lastRunIdRef.current = null
      prevRunStatusRef.current = null
      lastBatchSeqRef.current = runBatchSeq
      prevStatusesRef.current.clear()
      prevCatStatusesRef.current.clear()
      collapseTimersRef.current.forEach((t) => window.clearTimeout(t))
      collapseTimersRef.current = []
      setExpandedCategories(new Set())
      setExpandedCases(new Set())
      return
    }

    const isNewRunId = lastRunIdRef.current !== run.run_id
    const isNewBatchOnSameRun =
      !isNewRunId &&
      (lastBatchSeqRef.current !== runBatchSeq ||
        (prevRunStatusRef.current !== 'running' && run.status === 'running'))

    if (isNewRunId) {
      lastRunIdRef.current = run.run_id
      lastBatchSeqRef.current = runBatchSeq
      prevRunStatusRef.current = run.status
      prevStatusesRef.current.clear()
      prevCatStatusesRef.current.clear()
      collapseTimersRef.current.forEach((t) => window.clearTimeout(t))
      collapseTimersRef.current = []

      const initCats = new Set<string>()
      const initCases = new Set<string>()
      for (const c of run.cases) {
        prevStatusesRef.current.set(c.nodeid, c.status)
        if (c.status === 'running' || c.status === 'failed' || c.status === 'error') {
          initCats.add(`${c.domain}::${c.category_id}`)
          initCases.add(c.nodeid)
        }
      }
      // If no active/failed item remains (e.g. completed run), expand only categories that actually ran
      if (initCats.size === 0 && categories.length > 0) {
        const executedCats = categories.filter((c) => c.passed + c.failed + c.skipped > 0)
        if (executedCats.length > 0) {
          executedCats.forEach((c) => initCats.add(c.key))
        } else {
          initCats.add(categories[0].key)
        }
      }
      for (const cat of categories) {
        prevCatStatusesRef.current.set(cat.key, cat.status)
      }
      setExpandedCategories(initCats)
      setExpandedCases(initCases)
    } else if (isNewBatchOnSameRun) {
      lastBatchSeqRef.current = runBatchSeq
      prevRunStatusRef.current = run.status
      collapseTimersRef.current.forEach((t) => window.clearTimeout(t))
      collapseTimersRef.current = []
      prevStatusesRef.current.clear()
      prevCatStatusesRef.current.clear()
      for (const c of run.cases) {
        prevStatusesRef.current.set(c.nodeid, c.status)
      }
      for (const cat of categories) {
        prevCatStatusesRef.current.set(cat.key, cat.status)
      }
      setAutoFollow(true)
      setExpandedCategories(new Set())
      setExpandedCases(new Set())
    } else {
      prevRunStatusRef.current = run.status
      lastBatchSeqRef.current = runBatchSeq
    }
  }, [run, categories, runBatchSeq])

  // Track status transitions for Auto-Collapse & Auto-Focus
  useEffect(() => {
    if (!run) return
    const prevMap = prevStatusesRef.current

    for (const c of run.cases) {
      const prev = prevMap.get(c.nodeid)
      const catKey = `${c.domain}::${c.category_id}`

      if (prev !== c.status) {
        prevMap.set(c.nodeid, c.status)

        if (c.status === 'running') {
          if (autoFollow) {
            setExpandedCategories((s) => {
              const next = new Set(s)
              next.add(catKey)
              return next
            })
            setExpandedCases((s) => {
              const next = new Set(s)
              next.add(c.nodeid)
              return next
            })
            window.requestAnimationFrame(() => {
              const el = caseRefs.current.get(c.nodeid)
              el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
            })
          }
        } else if ((c.status === 'passed' || c.status === 'skipped') && prev === 'running') {
          if (autoFollow) {
            const targetNodeId = c.nodeid
            const timer = window.setTimeout(() => {
              setExpandedCases((s) => {
                if (!s.has(targetNodeId)) return s
                const next = new Set(s)
                next.delete(targetNodeId)
                return next
              })
            }, 480)
            collapseTimersRef.current.push(timer)
          }
        } else if (c.status === 'failed' || c.status === 'error') {
          // Always pin failures open
          setExpandedCategories((s) => {
            const next = new Set(s)
            next.add(catKey)
            return next
          })
          setExpandedCases((s) => {
            const next = new Set(s)
            next.add(c.nodeid)
            return next
          })
        }
      }
    }

    // Auto-collapse completed category when all cases pass/skip without failures
    const prevCatMap = prevCatStatusesRef.current
    for (const cat of categories) {
      const prevCat = prevCatMap.get(cat.key)
      if (prevCat !== cat.status) {
        prevCatMap.set(cat.key, cat.status)
        if (autoFollow && prevCat === 'running' && cat.status === 'passed' && cat.failed === 0) {
          const catKey = cat.key
          const timer = window.setTimeout(() => {
            setExpandedCategories((s) => {
              if (!s.has(catKey)) return s
              const next = new Set(s)
              next.delete(catKey)
              return next
            })
          }, 550)
          collapseTimersRef.current.push(timer)
        }
      }
    }
  }, [run, categories, autoFollow])

  const toggleCategory = useCallback((catKey: string) => {
    setExpandedCategories((s) => {
      const next = new Set(s)
      if (next.has(catKey)) next.delete(catKey)
      else next.add(catKey)
      return next
    })
  }, [])

  const toggleCase = useCallback((nodeid: string) => {
    setExpandedCases((s) => {
      const next = new Set(s)
      if (next.has(nodeid)) next.delete(nodeid)
      else next.add(nodeid)
      return next
    })
  }, [])

  const focusCase = useCallback((catKey: string, nodeid: string) => {
    setAutoFollow(false)
    setExpandedCategories((s) => {
      const next = new Set(s)
      next.add(catKey)
      return next
    })
    setExpandedCases((s) => {
      const next = new Set(s)
      next.add(nodeid)
      return next
    })
    window.requestAnimationFrame(() => {
      const el = caseRefs.current.get(nodeid)
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }, [])

  const expandAll = useCallback(() => {
    setAutoFollow(false)
    setExpandedCategories(new Set(categories.map((c) => c.key)))
    setExpandedCases(new Set(categories.flatMap((c) => c.cases.map((tc) => tc.nodeid))))
  }, [categories])

  const collapsePassed = useCallback(() => {
    const keepCats = new Set<string>()
    const keepCases = new Set<string>()
    for (const cat of categories) {
      if (cat.status === 'running' || cat.failed > 0) {
        keepCats.add(cat.key)
      }
      for (const tc of cat.cases) {
        if (tc.status === 'running' || tc.status === 'failed' || tc.status === 'error') {
          keepCases.add(tc.nodeid)
        }
      }
    }
    setExpandedCategories(keepCats)
    setExpandedCases(keepCases)
  }, [categories])

  return {
    autoFollow,
    setAutoFollow,
    expandedCategories,
    expandedCases,
    toggleCategory,
    toggleCase,
    focusCase,
    expandAll,
    collapsePassed,
    registerCaseRef,
  }
}
