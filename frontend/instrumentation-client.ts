/**
 * Browser-side error tracking.
 *
 * Next.js loads this file automatically on the client. With no
 * `NEXT_PUBLIC_SENTRY_DSN` set, `init` is skipped entirely and the app behaves
 * exactly as it did before — so local development and CI need no account.
 */

import * as Sentry from "@sentry/nextjs"

import { DSN, sharedOptions } from "@/lib/sentry-shared"

if (DSN) {
  Sentry.init({ dsn: DSN, ...sharedOptions })
}

// Lets Next report client-side navigation errors. Safe to export even when
// Sentry is not initialised — it becomes a no-op.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart
