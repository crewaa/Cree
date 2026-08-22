"use client"

/**
 * Tells the user when a request is taking unusually long, instead of leaving
 * them staring at a spinner.
 *
 * This exists because of where Crewaa is hosted. A Render service on the free
 * plan spins down after 15 minutes without traffic and takes about a minute to
 * wake up, so the first person to visit after a quiet spell waits ~60 seconds
 * for sign-in — with no feedback at all. Every one of them reasonably concludes
 * the site is broken and leaves.
 *
 * The honest fix is a plan that does not sleep. Until then, saying "the server
 * is waking up" turns an apparently broken product into a slow one, which is a
 * different and much more survivable impression.
 */

import { useEffect, useState } from "react"

/** Milliseconds before a request is considered slow enough to explain. */
const SLOW_AFTER_MS = 4000

export function useSlowRequestHint(active: boolean): boolean {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    if (!active) return

    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS)

    // Cleared on the way out rather than at the top of the effect: setting
    // state synchronously inside an effect body costs an extra render pass on
    // every submit, and is the pattern the React lint rule flags.
    return () => {
      clearTimeout(timer)
      setSlow(false)
    }
  }, [active])

  return slow
}

export const SLOW_REQUEST_MESSAGE =
  "Still working — the server may be waking up, which can take up to a minute."
