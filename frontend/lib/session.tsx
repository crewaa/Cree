"use client"

/**
 * Shared authenticated session.
 *
 * Before this existed, `(app)/layout.tsx` fetched `/users/me` and then every
 * dashboard page fetched it again independently — 19 identical requests were
 * observed in a single creator journey, each one gating render.
 *
 * The provider fetches once and every page reads from context.
 */

import { createContext, useContext, useEffect, useState } from "react"
import { usePathname, useRouter } from "next/navigation"

import { getCurrentUser } from "./user"
import { CurrentUser, Role } from "./types"

interface SessionValue {
  user: CurrentUser | null
  loading: boolean
  /** Clears the cached user, e.g. after logout. */
  clear: () => void
}

const SessionContext = createContext<SessionValue>({
  user: null,
  loading: true,
  clear: () => {},
})

/** The studio each role starts on. */
export const HOME_FOR_ROLE: Record<Role, string> = {
  ADMIN: "/dashboard/admin",
  BRAND: "/dashboard/brand",
  INFLUENCER: "/dashboard/influencer",
}

/**
 * Routes any authenticated user may open, regardless of role.
 *
 * This list is why the guard exists in this form. The previous implementation
 * checked `pathname.startsWith("/dashboard/<role>")`, which meant
 * `/dashboard/profile` and `/dashboard/analytics/*` did not match and users were
 * bounced back to their studio on every refresh, direct link or new tab —
 * including the profile page where a creator enters their social handles.
 */
const SHARED_PREFIXES = [
  "/dashboard/profile",
  "/dashboard/brand-profile",
  "/dashboard/analytics",
]

export function isRouteAllowed(role: Role, pathname: string): boolean {
  if (SHARED_PREFIXES.some((p) => pathname.startsWith(p))) return true
  return pathname.startsWith(HOME_FOR_ROLE[role])
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  // usePathname re-evaluates on client-side navigation; reading `location`
  // directly (as before) only ever saw the URL at mount.
  const pathname = usePathname()

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data = await getCurrentUser()
        if (cancelled) return
        setUser(data)
      } catch {
        if (!cancelled) router.replace("/login")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
    // Deliberately runs once: the session does not change between navigations.
  }, [router])

  // Role routing is a separate effect so it re-checks whenever the path changes.
  useEffect(() => {
    if (!user || !pathname) return
    if (!isRouteAllowed(user.role, pathname)) {
      router.replace(HOME_FOR_ROLE[user.role])
    }
  }, [user, pathname, router])

  return (
    <SessionContext.Provider value={{ user, loading, clear: () => setUser(null) }}>
      {children}
    </SessionContext.Provider>
  )
}

/** Current user + loading state. Returns `user: null` while loading. */
export function useSession() {
  return useContext(SessionContext)
}
