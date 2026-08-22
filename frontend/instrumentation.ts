/**
 * Server and edge error tracking for the Next.js layer.
 *
 * This covers crashes in server components, route handlers and middleware —
 * the failures that produce a blank page rather than a red banner, and which
 * are otherwise invisible because they never reach the browser console.
 *
 * The FastAPI backend has its own tracker (`app/core/observability.py`); these
 * are deliberately separate projects so an API outage does not drown the
 * frontend's issues.
 */

import * as Sentry from "@sentry/nextjs"

export async function register() {
  const { DSN, sharedOptions } = await import("@/lib/sentry-shared")
  if (!DSN) return

  // Both runtimes take the same options; only the entry point differs.
  if (
    process.env.NEXT_RUNTIME === "nodejs" ||
    process.env.NEXT_RUNTIME === "edge"
  ) {
    Sentry.init({ dsn: DSN, ...sharedOptions })
  }
}

/** Next.js calls this for uncaught server-side errors. */
export const onRequestError = Sentry.captureRequestError
