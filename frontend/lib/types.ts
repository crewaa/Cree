/**
 * Shared API types.
 *
 * These previously lived as `any` in every dashboard component, or were
 * re-declared locally per page. Keeping one definition means a backend schema
 * change surfaces as a typecheck failure instead of a runtime `undefined`.
 */

export type Role = "BRAND" | "INFLUENCER" | "ADMIN"

/** Shape of `GET /users/me`. */
export interface CurrentUser {
  id: number
  email: string
  role: Role
}

/** Shape of `GET /users/creator-profile`. */
export interface CreatorProfile {
  id: number
  user_id: number
  full_name: string
  location: string
  primary_platform: string
  category: string
  instagram_username?: string | null
  instagram_profile_link?: string | null
  youtube_username?: string | null
  youtube_profile_link?: string | null
  bio?: string | null
}

/** Shape of `GET /users/brand-profile`. */
export interface BrandProfile {
  id: number
  user_id: number
  brand_name: string
  industry: string
  description?: string | null
  website?: string | null
  logo_url?: string | null
  campaign_goal: string
  budget_range: string
  target_location?: string | null
  target_languages?: string | null
  platform_preferences?: string | null
}

/** Row from `GET /users/saved-creators`. */
export interface SavedCreator {
  id: number
  brand_id: number
  creator_id: number
  fit_level: string
  score_reasoning?: string | null
  saved_at: string
  creator_name?: string | null
  creator_category?: string | null
  creator_platform?: string | null
}

/** Outcome of the most recent background scrape, from `/…/scrape-status/{id}`. */
export interface ScrapeStatus {
  status: "none" | "running" | "success" | "error"
  message?: string | null
  started_at?: string | null
  finished_at?: string | null
}

/**
 * Narrow an unknown caught value to a message.
 *
 * The axios interceptor throws an `ApiError` (which extends `Error`), so the
 * message is the backend's `detail` field.
 */
export function errorMessage(err: unknown, fallback = "Something went wrong"): string {
  return err instanceof Error && err.message ? err.message : fallback
}
