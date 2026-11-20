import { useEffect, useState } from 'react'

/**
 * Ticks current epoch milliseconds at `intervalMs` only while `active` is true.
 * When inactive, no timer runs and no extra renders occur.
 */
export function useLiveNow(active: boolean, intervalMs = 500): number {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!active) return
    setNow(Date.now())
    const id = window.setInterval(() => {
      setNow(Date.now())
    }, intervalMs)
    return () => window.clearInterval(id)
  }, [active, intervalMs])

  return now
}
