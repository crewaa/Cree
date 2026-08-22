/**
 * Shared Sentry configuration for the browser, the server and the edge runtime.
 *
 * Kept in one place because the three runtimes each need their own init call,
 * and three copies of a privacy decision is three chances to get it wrong.
 *
 * The decisions, and why:
 *
 * - **No session replay.** Replay records the user's screen. On this app that
 *   screen shows a creator's private analytics, or a brand's campaign budget.
 *   Recording it to debug a layout bug is not a trade worth making.
 * - **No PII.** Sentry can attach the user's IP and, with some integrations,
 *   their email. Neither is needed to fix a crash.
 * - **Tracing off by default.** It is billed separately from errors.
 * - **Bearer tokens scrubbed.** The JWT lives in `localStorage` and is attached
 *   to every request, so it can surface in a breadcrumb or a failed-request URL.
 */

import type { Breadcrumb, ErrorEvent } from "@sentry/nextjs"

const BEARER = /(?<=\bBearer\s)[A-Za-z0-9._-]{8,}/gi
/** A JWT that has escaped into a URL or a message on its own. */
const BARE_JWT = /\beyJ[A-Za-z0-9._-]{20,}/g

export const REDACTED = "[redacted]"

export function scrubText(value: string): string {
  return value.replace(BEARER, REDACTED).replace(BARE_JWT, REDACTED)
}

/** Walk an event and strip anything token-shaped, at any depth. */
export function scrubEvent<T>(value: T, depth = 0): T {
  if (depth > 8 || value == null) return value
  if (typeof value === "string") return scrubText(value) as unknown as T
  if (Array.isArray(value)) {
    return value.map((v) => scrubEvent(v, depth + 1)) as unknown as T
  }
  if (typeof value === "object") {
    const out: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      out[key] = /token|auth|secret|password|cookie|session/i.test(key)
        ? REDACTED
        : scrubEvent(item, depth + 1)
    }
    return out as unknown as T
  }
  return value
}

export const sharedOptions = {
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV,
  sendDefaultPii: false,
  tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? 0),
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,
  maxBreadcrumbs: 25,
  // Noise that is never actionable: a user navigating away mid-request, or a
  // browser extension throwing inside our page.
  ignoreErrors: [
    "AbortError",
    "Non-Error promise rejection captured",
    "ResizeObserver loop completed with undelivered notifications",
  ],
  beforeSend(event: ErrorEvent): ErrorEvent {
    return scrubEvent(event)
  },
  beforeBreadcrumb(breadcrumb: Breadcrumb): Breadcrumb {
    return scrubEvent(breadcrumb)
  },
}

/** Blank in every environment that has not configured Sentry, which is fine. */
export const DSN = process.env.NEXT_PUBLIC_SENTRY_DSN || ""
