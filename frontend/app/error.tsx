"use client"

import { useEffect } from "react"
import * as Sentry from "@sentry/nextjs"

/**
 * Root error boundary.
 *
 * Without this, a thrown render error produced a blank white screen with no
 * explanation and no recovery path.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Unhandled application error:", error)
    // A render crash caught by a boundary never reaches window.onerror, so
    // without this the most visible failure in the app — a broken page — would
    // be the one thing the tracker never heard about. No-op without a DSN.
    Sentry.captureException(error)
  }, [error])

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#06070C] px-6 text-center text-white">
      <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
        Something went wrong
      </h1>
      <p className="mt-4 max-w-md text-gray-400">
        The page failed to load. Trying again usually fixes it — if it keeps
        happening, please let us know.
      </p>
      {error.digest && (
        <p className="mt-3 font-mono text-xs text-gray-600">
          Reference: {error.digest}
        </p>
      )}
      <button
        onClick={reset}
        className="mt-10 rounded-xl bg-white px-6 py-3 font-medium text-black transition hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
      >
        Try again
      </button>
    </main>
  )
}
