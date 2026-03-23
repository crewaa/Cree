import { api } from "./axios"

export async function createBrandProfile(data: {
  brand_name: string
  industry: string
  description?: string
  website?: string
  logo_url?: string
  campaign_goal?: string
  budget_range?: string
  target_location?: string
  target_languages?: string
  platform_preferences?: string
}) {
  const res = await api.post("/users/brand-profile", data)
  return res.data
}

export async function getBrandProfile() {
  const res = await api.get("/users/brand-profile")
  return res.data
}

export async function updateBrandProfile(data: {
  brand_name: string
  industry: string
  description?: string
  website?: string
  logo_url?: string
  campaign_goal?: string
  budget_range?: string
  target_location?: string
  target_languages?: string
  platform_preferences?: string
}) {
  const res = await api.put("/users/brand-profile", data)
  return res.data
}
