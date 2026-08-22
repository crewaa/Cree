import { api } from "./axios"

// --- Types ---
export interface PlatformStats {
  total_users: number
  total_creators: number
  total_brands: number
  total_admins: number
  new_users_last_7_days: number
}

export interface AdminUserListItem {
  id: number
  email: string
  role: string
  is_active: boolean
  has_profile: boolean
  created_at: string
}

export interface AdminUserDetail {
  id: number
  email: string
  role: string
  is_active: boolean
  created_at: string
  // Creator
  creator_full_name?: string
  creator_location?: string
  creator_category?: string
  creator_primary_platform?: string
  creator_instagram_username?: string
  creator_youtube_username?: string
  creator_bio?: string
  creator_profile_completed?: boolean
  /** Named fields still to fill in, so the flag is actionable. */
  creator_profile_missing?: string[]
  // Brand
  brand_name?: string
  brand_industry?: string
  brand_description?: string
  brand_website?: string
  brand_campaign_goal?: string
  brand_budget_range?: string
  brand_profile_completed?: boolean
  brand_profile_missing?: string[]
}

export interface PaginatedUsers {
  items: AdminUserListItem[]
  total: number
  page: number
  page_size: number
}

// --- API Calls ---
export async function getAdminStats(): Promise<PlatformStats> {
  const res = await api.get("/admin/stats")
  return res.data
}

export async function getAdminUsers(params?: {
  role?: string
  search?: string
  page?: number
  page_size?: number
}): Promise<PaginatedUsers> {
  const res = await api.get("/admin/users", { params })
  return res.data
}

export async function getAdminUserDetail(id: number): Promise<AdminUserDetail> {
  const res = await api.get(`/admin/users/${id}`)
  return res.data
}

export async function deleteAdminUser(id: number): Promise<void> {
  await api.delete(`/admin/users/${id}`)
}

export async function createAdminUser(data: {
  email: string
  password: string
  role: string
}): Promise<AdminUserDetail> {
  const res = await api.post("/admin/users", data)
  return res.data
}
