import { useCallback, useEffect, useRef, useState } from 'react'
import { formatDuration, type RunState, type RunStatus } from '../types/run'

export type NotificationPermissionState = NotificationPermission | 'unsupported'

const STORAGE_KEY = 'psi_dashboard_notifications'
const DEFAULT_TITLE = 'PSI QA Automation Monitor'
const SHORT_TITLE = 'PSI QA Monitor'

type FaviconTone = 'idle' | 'running' | 'running-fail' | 'passed' | 'failed' | 'stopped'

const FAVICON_COLORS: Record<FaviconTone, { bg: string; dot: string }> = {
  idle: { bg: '#1e293b', dot: '#64748b' },
  running: { bg: '#1e3a8a', dot: '#60a5fa' },
  'running-fail': { bg: '#7f1d1d', dot: '#f87171' },
  passed: { bg: '#064e3b', dot: '#34d399' },
  failed: { bg: '#7f1d1d', dot: '#f87171' },
  stopped: { bg: '#78350f', dot: '#fbbf24' },
}

function buildFaviconDataUrl(tone: FaviconTone): string {
  const { bg, dot } = FAVICON_COLORS[tone]
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="${bg}"/><circle cx="16" cy="16" r="7" fill="${dot}"/></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

function getFaviconTone(run: RunState | null): FaviconTone {
  if (!run) return 'idle'
  if (run.status === 'running') {
    return run.summary.failed > 0 ? 'running-fail' : 'running'
  }
  if (run.status === 'stopped') return 'stopped'
  if (run.summary.failed > 0 || run.status === 'failed') return 'failed'
  if (run.status === 'completed') return 'passed'
  return 'idle'
}

export function formatTabTitle(run: RunState | null): string {
  if (!run) return DEFAULT_TITLE

  const { completed, total, passed, failed } = run.summary
  if (run.status === 'running') {
    if (total === 0) return `[수집중] ${SHORT_TITLE}`
    if (failed > 0) return `[실행중 ${completed}/${total} · 오류 ${failed}] ${SHORT_TITLE}`
    return `[실행중 ${completed}/${total}] ${SHORT_TITLE}`
  }

  if (run.status === 'stopped') {
    return `[중단됨 ${completed}/${total}] ${SHORT_TITLE}`
  }

  if (failed > 0 || run.status === 'failed') {
    return failed > 0 ? `[오류 ${failed}건] ${SHORT_TITLE}` : `[실패] ${SHORT_TITLE}`
  }

  if (run.status === 'completed') {
    return `[완료 ${passed}/${total}] ${SHORT_TITLE}`
  }

  return DEFAULT_TITLE
}

function getInitialPermission(): NotificationPermissionState {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported'
  }
  return Notification.permission
}

function getInitialPref(): 'true' | 'false' | null {
  if (typeof window === 'undefined') return null
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === 'true' || raw === 'false') return raw
  return null
}

function isWindowUnfocused(): boolean {
  if (typeof document === 'undefined') return false
  return document.hidden || !document.hasFocus()
}

export interface UseRunNotificationsResult {
  permission: NotificationPermissionState
  enabled: boolean
  toggleNotifications: () => Promise<void>
  ensurePermission: () => Promise<void>
}

export function useRunNotifications(
  run: RunState | null,
  runBatchSeq: number,
): UseRunNotificationsResult {
  const [permission, setPermission] = useState<NotificationPermissionState>(getInitialPermission)
  const [enabledPref, setEnabledPref] = useState<'true' | 'false' | null>(getInitialPref)

  const lastFaviconToneRef = useRef<FaviconTone | null>(null)
  const prevStateRef = useRef<{
    runId: string
    status: RunStatus
    batchSeq: number
    alertedFailure: boolean
  } | null>(null)

  const enabled = permission === 'granted' && enabledPref !== 'false'

  // Sync permission if user changes browser site settings while tab is open
  useEffect(() => {
    if (permission === 'unsupported') return
    const syncPermission = () => {
      if ('Notification' in window) {
        setPermission(Notification.permission)
      }
    }
    window.addEventListener('focus', syncPermission)
    return () => window.removeEventListener('focus', syncPermission)
  }, [permission])

  const sendNotification = useCallback(
    (title: string, body: string, tag: string, tone: FaviconTone, renotify = false) => {
      if (permission !== 'granted' || enabledPref === 'false') return
      try {
        const notification = new Notification(title, {
          body,
          tag,
          icon: buildFaviconDataUrl(tone),
          renotify,
        } as NotificationOptions)
        notification.onclick = () => {
          window.focus()
          notification.close()
        }
      } catch {
        // Ignore environments where Notification constructor is restricted
      }
    },
    [enabledPref, permission],
  )

  const toggleNotifications = useCallback(async () => {
    if (permission === 'unsupported' || permission === 'denied') return

    if (permission === 'default') {
      try {
        const result = await Notification.requestPermission()
        setPermission(result)
        if (result === 'granted') {
          localStorage.setItem(STORAGE_KEY, 'true')
          setEnabledPref('true')
          try {
            const n = new Notification('PSI QA Monitor 알림 활성화', {
              body: '테스트 완료 또는 오류 발생 시 브라우저 알림을 표시합니다.',
              tag: 'psi-qa-notify-enabled',
              icon: buildFaviconDataUrl('passed'),
            })
            n.onclick = () => {
              window.focus()
              n.close()
            }
          } catch {
            // ignore
          }
        } else {
          localStorage.setItem(STORAGE_KEY, 'false')
          setEnabledPref('false')
        }
      } catch {
        // ignore permission prompt errors
      }
      return
    }

    const next: 'true' | 'false' = enabled ? 'false' : 'true'
    localStorage.setItem(STORAGE_KEY, next)
    setEnabledPref(next)
  }, [enabled, permission])

  const ensurePermission = useCallback(async () => {
    if (permission !== 'default' || enabledPref === 'false') return
    try {
      const result = await Notification.requestPermission()
      setPermission(result)
      if (result === 'granted') {
        localStorage.setItem(STORAGE_KEY, 'true')
        setEnabledPref('true')
      }
    } catch {
      // ignore
    }
  }, [enabledPref, permission])

  // Update browser tab title and status favicon
  useEffect(() => {
    document.title = formatTabTitle(run)

    const tone = getFaviconTone(run)
    if (lastFaviconToneRef.current !== tone) {
      lastFaviconToneRef.current = tone
      let link = document.querySelector<HTMLLinkElement>('link[rel="icon"][data-psi-favicon]')
      if (!link) {
        link = document.createElement('link')
        link.rel = 'icon'
        link.type = 'image/svg+xml'
        link.setAttribute('data-psi-favicon', 'true')
        document.head.appendChild(link)
      }
      link.href = buildFaviconDataUrl(tone)
    }
  }, [run])

  useEffect(() => {
    return () => {
      document.title = DEFAULT_TITLE
    }
  }, [])

  // Detect live run transitions and fire browser notifications
  useEffect(() => {
    if (!run) {
      prevStateRef.current = null
      return
    }

    const prev = prevStateRef.current
    const isSameRun = prev !== null && prev.runId === run.run_id
    const isNewBatch = isSameRun && prev.batchSeq !== runBatchSeq
    let alertedFailure = isSameRun && !isNewBatch ? prev.alertedFailure : false

    if (isSameRun) {
      // Mid-run early failure alert (only once per batch when user is away and more cases remain)
      if (
        run.status === 'running' &&
        !alertedFailure &&
        run.summary.failed > 0 &&
        run.summary.pending > 1 &&
        isWindowUnfocused()
      ) {
        alertedFailure = true
        sendNotification(
          `⚠️ QA 테스트 오류 감지 (${run.summary.failed}건)`,
          `${run.title}\n진행 ${run.summary.completed}/${run.summary.total} (나머지 항목 실행 중)`,
          `psi-qa-run-${run.run_id}`,
          'running-fail',
          false,
        )
      }

      // Final transition from running -> completed / failed / stopped
      if (prev.status === 'running' && run.status !== 'running') {
        const { total, completed, passed, failed, skipped, duration_sec } = run.summary
        const durationText = formatDuration(duration_sec)
        const tag = `psi-qa-run-${run.run_id}`

        if (run.status === 'stopped') {
          sendNotification(
            `⏹️ QA 테스트 중단됨 (${completed}/${total})`,
            `${run.title}\n정상 ${passed} · 오류 ${failed} · 잔여 ${run.summary.pending}`,
            tag,
            'stopped',
            true,
          )
        } else if (failed > 0 || run.status === 'failed') {
          const headline =
            failed > 0 ? `❌ QA 테스트 오류 (${failed}건 실패)` : '❌ QA 테스트 실패'
          sendNotification(
            headline,
            `${run.title}\n정상 ${passed} · 오류 ${failed} · 제외 ${skipped} (${durationText})`,
            tag,
            'failed',
            true,
          )
        } else {
          sendNotification(
            `✅ QA 테스트 완료 (${passed}/${total} 정상)`,
            `${run.title}\n제외 ${skipped} · 소요시간 ${durationText}`,
            tag,
            'passed',
            true,
          )
        }
      }
    }

    prevStateRef.current = {
      runId: run.run_id,
      status: run.status,
      batchSeq: runBatchSeq,
      alertedFailure,
    }
  }, [run, runBatchSeq, sendNotification])

  return {
    permission,
    enabled,
    toggleNotifications,
    ensurePermission,
  }
}
