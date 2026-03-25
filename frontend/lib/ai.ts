import { api } from "./axios"

export async function discoverCreators(data: {
  niche: string
  budget_range: string
  campaign_goal: string
  target_location?: string
  target_languages?: string[]
  platform_preferences?: string[]
}) {
  const res = await api.post("/ai/discover-creators", data)
  return res.data
}

export async function getBrandDeals() {
  const res = await api.post("/ai/brand-deals")
  return res.data
}

export async function getCachedBrandDeals() {
  const res = await api.get("/ai/brand-deals")
  return res.data
}

export async function getCreatorSummary() {
  const res = await api.post("/ai/creator-summary")
  return res.data
}

export async function getCachedCreatorSummary() {
  const res = await api.get("/ai/creator-summary")
  return res.data
}
