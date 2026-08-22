"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

import { HOME_FOR_ROLE, useSession } from "@/lib/session"

/**
 * `/dashboard` has no content of its own — it used to render the literal text
 * "Landing Page". It now forwards to the studio for the caller's role.
 */
export default function DashboardIndex() {
  const router = useRouter()
  const { user, loading } = useSession()

  useEffect(() => {
    if (!loading && user) router.replace(HOME_FOR_ROLE[user.role])
  }, [user, loading, router])

  return (
    <div className="flex min-h-[60vh] items-center justify-center" aria-busy="true">
      <span className="sr-only">Taking you to your dashboard…</span>
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
    </div>
  )
}
