import { api } from "./axios"

/**
 * Rank creators for a campaign.
 *
 * Pass `campaign_id` to search against a saved campaign — the server then reads
 * niche, goal, location, platforms and the follower floor from that record and
 * ignores the loose fields. Pass `niche` for an ad-hoc search instead. One or
 * the other is required.
 */
export async function discoverCreators(data: {
  campaign_id?: number
  niche?: string
  budget_range?: string
  campaign_goal?: string
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

/**
 * Stream brand deals, invoking `onDeal` as each one arrives.
 *
 * The batch endpoint makes the creator wait for the *slowest* brand before
 * seeing anything — 10-20 seconds of spinner. This reads the NDJSON stream so
 * the first card appears as soon as the first assessment returns.
 *
 * Uses `fetch` rather than the axios instance because axios in the browser
 * buffers the whole body before resolving, which would defeat the point. The
 * bearer token is attached by hand for the same reason.
 */
export async function streamBrandDeals(
  onDeal: (deal: unknown) => void,
  signal?: AbortSignal
): Promise<{ total: number; generated_at?: string }> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/ai/brand-deals/stream`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal,
  })

  if (!res.ok) {
    // Failures available before the first byte still arrive as a status code.
    if (res.status === 429) {
      throw new Error("You've reached the limit for now. Please try again in a little while.")
    }
    throw new Error("Failed to load brand deals. Please try again.")
  }
  if (!res.body) throw new Error("Streaming is not supported in this browser.")

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let summary = { total: 0 } as { total: number; generated_at?: string }

  const handle = (line: string) => {
    if (!line.trim()) return
    const msg = JSON.parse(line)
    if (msg.type === "opportunity") onDeal(msg.opportunity)
    else if (msg.type === "done") summary = { total: msg.total, generated_at: msg.generated_at }
    // Once the response has started there is no status code left to change, so
    // the server reports late failures in-band.
    else if (msg.type === "error") throw new Error(msg.detail)
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // A chunk can split a line anywhere, so only whole lines are parsed and the
    // remainder is carried into the next read.
    const lines = buffer.split("\n")
    buffer = lines.pop() ?? ""
    for (const line of lines) handle(line)
  }
  handle(buffer)

  return summary
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

export async function expressInterest(opportunityId: string, message?: string) {
  const res = await api.post("/ai/opportunities/interest", {
    opportunity_id: opportunityId,
    message,
  })
  return res.data
}

export async function withdrawInterest(opportunityId: string) {
  const res = await api.delete(`/ai/opportunities/interest/${opportunityId}`)
  return res.data
}

export async function getInterestedCreators() {
  const res = await api.get("/ai/interested-creators")
  return res.data
}
