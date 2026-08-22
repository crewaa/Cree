import { api } from "./axios"

/**
 * A campaign is what a brand is actually offering.
 *
 * Every commercial field here is typed by the brand. The AI never authors any
 * of them — it only judges which creators fit.
 */
export interface Campaign {
  id: number
  name: string
  status: "draft" | "active" | "closed"
  niche: string
  campaign_goal: string
  campaign_type: string
  budget_per_creator?: number | null
  currency: string
  deliverables?: string[] | null
  deadline?: string | null
  brief?: string | null
  platform_preferences?: string[] | null
  target_location?: string | null
  min_followers?: number | null
  creators_needed?: number | null
  is_open_to_applications: boolean
  created_at: string
  interested_count: number
}

export interface CampaignInput {
  name: string
  niche: string
  campaign_goal: string
  campaign_type: string
  budget_per_creator?: number | null
  currency?: string
  deliverables?: string[] | null
  deadline?: string | null
  brief?: string | null
  platform_preferences?: string[] | null
  target_location?: string | null
  min_followers?: number | null
  creators_needed?: number | null
  is_open_to_applications?: boolean
}

export async function listCampaigns(): Promise<Campaign[]> {
  const res = await api.get("/campaigns")
  return res.data
}

export async function getCampaign(id: number): Promise<Campaign> {
  const res = await api.get(`/campaigns/${id}`)
  return res.data
}

export async function createCampaign(data: CampaignInput): Promise<Campaign> {
  const res = await api.post("/campaigns", data)
  return res.data
}

export async function updateCampaign(id: number, data: CampaignInput): Promise<Campaign> {
  const res = await api.put(`/campaigns/${id}`, data)
  return res.data
}

/** Closes rather than deletes — creators may already have applied. */
export async function closeCampaign(id: number): Promise<void> {
  await api.delete(`/campaigns/${id}`)
}
