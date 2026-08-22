"use client"

import { useSession } from "@/lib/session"

/**
 * Admin section wrapper.
 *
 * The role check now reads the shared session rather than issuing its own
 * `/users/me` request — opening an admin page previously cost two identical
 * round-trips. `SessionProvider` already redirects a non-admin away from
 * `/dashboard/admin`, so this only has to handle the loading state.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useSession()

  if (loading || user?.role !== "ADMIN") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center" aria-busy="true">
        <span className="sr-only">Loading the admin console…</span>
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
      </div>
    )
  }

  return <main className="p-6">{children}</main>
}
