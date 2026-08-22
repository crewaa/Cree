"use client"

/**
 * Whether the signed-in user has completed the profile their studio needs.
 *
 * Both studios depend on a profile: a creator's AI tools need social handles to
 * analyse, and brand discovery needs an industry to match against. Nothing
 * checked before, so a new user could click into a feature that failed several
 * seconds later with a raw 404 and no way forward.
 *
 * Backed by `GET /users/profile-status`, which answers with 200 either way.
 * The earlier version probed the profile endpoint and caught the 404 — correct,
 * but it logged a console error on every dashboard load.
 */

import { useEffect, useState } from "react"

import { api } from "./axios"

interface ProfileStatus {
  /** null while loading. */
  hasProfile: boolean | null
  hasSocialHandles: boolean
  loading: boolean
}

export function useProfileStatus(): ProfileStatus {
  const [state, setState] = useState<{ has: boolean | null; social: boolean }>({
    has: null,
    social: false,
  })

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const res = await api.get("/users/profile-status")
        if (!cancelled) {
          setState({
            has: Boolean(res.data?.has_profile),
            social: Boolean(res.data?.has_social_handles),
          })
        }
      } catch {
        // Treat an unreachable check as "complete" so a transient failure never
        // locks a user out of features they already have access to.
        if (!cancelled) setState({ has: true, social: true })
      }
    }

    check()
    return () => {
      cancelled = true
    }
  }, [])

  return {
    hasProfile: state.has,
    hasSocialHandles: state.social,
    loading: state.has === null,
  }
}

/** Kept as named aliases so the studios read clearly. */
export const useHasCreatorProfile = useProfileStatus
export const useHasBrandProfile = useProfileStatus
