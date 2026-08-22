"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Check, Clock, Loader2, RefreshCw, Sparkles, Tag } from "lucide-react"
import { streamBrandDeals, getCachedBrandDeals, expressInterest, withdrawInterest } from "@/lib/ai"
import { errorMessage } from "@/lib/types"

type BrandDeal = {
  opportunity_id: string
  fit_level?: string
  industry_hint?: string
  campaign_type?: string
  campaign_requirements?: string
  compensation?: string
  timeline?: string
  deliverables?: string[]
  status?: string
  /** Set by the brand on its profile — not model-generated. */
  budget_range?: string
  /** True when compensation/timeline/deliverables are AI estimates. */
  terms_are_estimated?: boolean
  interested?: boolean
  // Real terms — present when the opportunity came from a brand's campaign.
  budget_per_creator?: number | null
  currency?: string | null
  deadline?: string | null
  what_to_expect?: string | null
  why_it_fits?: string[] | null
}

type DealsResponse = {
  opportunities: BrandDeal[]
  total: number
  generated_at?: string | null
  /** True once the batch predates the creator's current numbers. */
  is_stale?: boolean
}

export default function BrandDealsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  // Distinct from `loading`: cards are already on screen and more are coming,
  // so the page must render results and a progress note at the same time.
  const [streaming, setStreaming] = useState(false)
  const [deals, setDeals] = useState<DealsResponse | null>(null)
  const [error, setError] = useState("")
  const [pending, setPending] = useState<string | null>(null)

  useEffect(() => {
    async function initDeals() {
      try {
        const cached = await getCachedBrandDeals()
        if (cached) {
          setDeals(cached)
        }
      } catch (err) {
        // Ignore cache miss
      } finally {
        setLoading(false)
      }
    }
    initDeals()
  }, [])

  async function fetchDeals() {
    setStreaming(true)
    setError("")
    // Clear first so a refresh cannot interleave new cards with stale ones.
    setDeals({ opportunities: [], total: 0 })

    try {
      const summary = await streamBrandDeals((deal) => {
        setDeals((prev) => {
          const opportunities = [...(prev?.opportunities ?? []), deal as BrandDeal]
          return { ...prev, opportunities, total: opportunities.length }
        })
      })
      setDeals((prev) => ({
        opportunities: prev?.opportunities ?? [],
        total: prev?.opportunities.length ?? 0,
        generated_at: summary.generated_at,
        is_stale: false,
      }))
    } catch (err) {
      // Anything already streamed stays on screen — a failure on the fourth
      // brand should not discard the three that succeeded.
      setDeals((prev) => (prev?.opportunities.length ? prev : null))
      setError(errorMessage(err, "Failed to load brand deals. Please try again."))
    } finally {
      setStreaming(false)
    }
  }

  async function toggleInterest(deal: BrandDeal) {
    setPending(deal.opportunity_id)
    setError("")
    try {
      if (deal.interested) {
        await withdrawInterest(deal.opportunity_id)
      } else {
        await expressInterest(deal.opportunity_id)
      }
      // Reflect immediately; the server is the source of truth on next load.
      setDeals((prev) =>
        prev
          ? {
              ...prev,
              opportunities: prev.opportunities.map((o) =>
                o.opportunity_id === deal.opportunity_id
                  ? { ...o, interested: !deal.interested }
                  : o
              ),
            }
          : prev
      )
    } catch (err) {
      setError(errorMessage(err, "Could not register your interest."))
    } finally {
      setPending(null)
    }
  }

  const fitColors: Record<string, string> = {
    High: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    Medium: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    Low: "bg-red-500/20 text-red-300 border-red-500/30",
  }

  const statusColors: Record<string, string> = {
    open: "bg-emerald-500/20 text-emerald-300",
    closed: "bg-red-500/20 text-red-300",
  }

  return (
    <div className="relative relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/15 blur-[160px]" />
        <div className="absolute bottom-[-30%] left-[15%] h-[400px] w-[400px] rounded-full bg-cyan-500/10 blur-[140px]" />
      </div>

      <main className="relative z-10 max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <button
          onClick={() => router.back()}
          className="text-gray-400 hover:text-white text-sm mb-8 flex items-center gap-2 transition cursor-pointer"
        >
          ← Back to Creator Studio
        </button>

        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight mb-3">
          Brand Deals
        </h1>
        <p className="text-lg text-gray-400 mb-10">
          AI-curated brand collaboration opportunities matched to your profile.
        </p>

        {/* Loading — only until the first card lands; after that the results
            render and a smaller note carries the remaining progress. */}
        {(loading || (streaming && !deals?.opportunities.length)) && (
          <div className="flex flex-col items-center justify-center py-24 space-y-6">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-indigo-500/30 rounded-full animate-spin border-t-indigo-500" />
            </div>
            <div className="text-center">
              <p className="text-xl font-medium text-white">Finding opportunities for you...</p>
              <p className="text-gray-400 mt-2">AI is matching brands to your profile</p>
            </div>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-xl text-center mb-8">
            <p className="text-red-300 mb-4">{error}</p>
            <button
              onClick={fetchDeals}
              className="text-sm text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Initial CTA — shown before any fetch */}
        {!loading && !streaming && !deals && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-6">
            <Tag className="mx-auto h-10 w-10 text-gray-600" aria-hidden="true" />
            <div>
              <p className="text-2xl font-semibold text-white">Find Brand Deals For You</p>
              <p className="text-gray-400 mt-2 max-w-md mx-auto">
                Our AI analyzes your creator profile and matches you with relevant brand collaborations in real-time.
              </p>
            </div>
            <button
              onClick={fetchDeals}
              className="mt-4 rounded-full bg-white px-10 py-4 text-base font-semibold text-black hover:bg-gray-100 transition"
            >
              <span className="flex items-center gap-2"><Sparkles className="h-4 w-4" /> Find My Deals</span>
            </button>
          </div>
        )}

        {/* Results. Rendered during streaming too — cards appear one at a
            time rather than all at the end. */}
        {!loading && deals && (deals.opportunities.length > 0 || !streaming) && (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold">
                {deals.total} {deals.total === 1 ? "Opportunity" : "Opportunities"} Available
              </h2>
              {streaming ? (
                <span className="flex items-center gap-1.5 text-sm text-gray-400">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  Still searching…
                </span>
              ) : (
                <button
                  onClick={fetchDeals}
                  className="text-sm text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
                >
                  <span className="flex items-center gap-1.5"><RefreshCw className="h-3.5 w-3.5" /> Refresh</span>
                </button>
              )}
            </div>

            {deals.is_stale && (
              <p className="flex items-start gap-2 rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                <Clock className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                These matches were generated{" "}
                {deals.generated_at
                  ? new Date(deals.generated_at).toLocaleDateString()
                  : "a while ago"}{" "}
                and may not reflect your current audience. Refresh for an up-to-date list.
              </p>
            )}

            {deals.total === 0 ? (
              <div className="text-center py-16">
                <Tag className="mx-auto mb-4 h-8 w-8 text-gray-600" aria-hidden="true" />
                <p className="text-xl text-gray-400">No brand deals available right now</p>
                <p className="text-gray-500 text-sm mt-2">
                  Check back later — new opportunities are added as brands join the platform.
                </p>
              </div>
            ) : (
              <div className="grid gap-6 md:grid-cols-2">
                {deals.opportunities.map((deal) => (
                  <div
                    key={deal.opportunity_id}
                    className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-6 transition-all duration-300 hover:border-white/20 hover:-translate-y-1"
                  >
                    {/* Top bar */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        {deal.fit_level && (
                          <span className={`px-3 py-1 rounded-full text-xs font-medium border ${fitColors[deal.fit_level] || fitColors["Low"]}`}>
                            {deal.fit_level} Fit
                          </span>
                        )}
                        {deal.status && (
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[deal.status] || statusColors["open"]}`}>
                            {deal.status.toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Industry & Campaign */}
                    {deal.industry_hint && (
                      <div className="mb-3">
                        <span className="text-xs text-gray-500 uppercase tracking-wide">Industry</span>
                        <p className="text-lg font-semibold text-white mt-1">{deal.industry_hint}</p>
                      </div>
                    )}

                    {deal.campaign_type && (
                      <div className="mb-3">
                        <span className="text-xs text-gray-500 uppercase tracking-wide">Campaign Type</span>
                        <p className="text-sm text-indigo-300 mt-1">{deal.campaign_type}</p>
                      </div>
                    )}

                    {/* Requirements */}
                    {deal.campaign_requirements && (
                      <div className="mb-3">
                        <span className="text-xs text-gray-500 uppercase tracking-wide">Requirements</span>
                        <p className="text-sm text-gray-300 mt-1">{deal.campaign_requirements}</p>
                      </div>
                    )}

                    {/* Real terms, typed by the brand — no estimate language */}
                    {deal.terms_are_estimated === false && (
                      <>
                        <div className="mb-3 grid grid-cols-2 gap-4">
                          {deal.budget_per_creator != null && (
                            <div>
                              <span className="text-xs uppercase tracking-wide text-gray-500">
                                Fee
                              </span>
                              <p className="mt-1 text-sm font-medium text-emerald-300">
                                ₹{deal.budget_per_creator.toLocaleString()}
                              </p>
                            </div>
                          )}
                          {deal.deadline && (
                            <div>
                              <span className="text-xs uppercase tracking-wide text-gray-500">
                                Deadline
                              </span>
                              <p className="mt-1 text-sm text-gray-300">
                                {new Date(deal.deadline).toLocaleDateString()}
                              </p>
                            </div>
                          )}
                        </div>

                        {deal.what_to_expect && (
                          <div className="mb-3">
                            <span className="text-xs uppercase tracking-wide text-gray-500">
                              What to expect
                            </span>
                            <p className="mt-1 text-sm text-gray-300">{deal.what_to_expect}</p>
                          </div>
                        )}

                        {!!deal.why_it_fits?.length && (
                          <div className="mb-3">
                            <span className="text-xs uppercase tracking-wide text-gray-500">
                              Why you
                            </span>
                            <ul className="mt-2 space-y-1">
                              {deal.why_it_fits.map((r, j) => (
                                <li key={j} className="flex items-start gap-2 text-sm text-emerald-300/80">
                                  <Check className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {r}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    )}

                    {/* Budget band — verified, set by the brand */}
                    {deal.terms_are_estimated !== false && deal.budget_range && (
                      <div className="mb-3">
                        <span className="text-xs text-gray-500 uppercase tracking-wide">
                          Brand budget band
                        </span>
                        <p className="mt-1 flex items-center gap-1.5 text-sm font-medium text-white">
                          <Tag className="h-3.5 w-3.5 text-gray-400" />
                          {deal.budget_range}
                        </p>
                      </div>
                    )}

                    {/* Estimates — generated, explicitly not an offer */}
                    <div className={`grid grid-cols-2 gap-4 mb-3 ${deal.terms_are_estimated === false ? "hidden" : ""}`}>
                      {deal.compensation && (
                        <div>
                          <span className="text-xs text-gray-500 uppercase tracking-wide">
                            Indicative fee
                          </span>
                          <p className="text-sm text-emerald-300 mt-1 font-medium">{deal.compensation}</p>
                        </div>
                      )}
                      {deal.timeline && (
                        <div>
                          <span className="text-xs text-gray-500 uppercase tracking-wide">
                            Indicative timeline
                          </span>
                          <p className="text-sm text-gray-300 mt-1">{deal.timeline}</p>
                        </div>
                      )}
                    </div>

                    {/* Deliverables */}
                    {deal.deliverables && deal.deliverables.length > 0 && (
                      <div>
                        <span className="text-xs text-gray-500 uppercase tracking-wide">
                          {deal.terms_are_estimated === false ? "Deliverables" : "Suggested deliverables"}
                        </span>
                        <ul className="mt-2 space-y-1">
                          {deal.deliverables.map((d, j) => (
                            <li key={j} className="text-sm text-gray-300 flex items-start gap-2">
                              <span className="mt-0.5 text-indigo-400">•</span> {d}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* The card previously presented these figures as an offer.
                        They are generated from the brand's budget band, so they
                        are labelled and the creator is told terms are agreed
                        directly. */}
                    {deal.terms_are_estimated !== false && (
                      <p className="mt-4 flex items-start gap-2 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2 text-xs text-gray-400">
                        <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-500" aria-hidden="true" />
                        AI-generated estimate based on the brand&apos;s budget band. Final
                        fee, timeline and deliverables are agreed directly with the brand.
                      </p>
                    )}

                    <button
                      onClick={() => toggleInterest(deal)}
                      disabled={pending === deal.opportunity_id}
                      aria-pressed={deal.interested}
                      className={`mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-medium transition disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${
                        deal.interested
                          ? "border border-emerald-500/40 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25"
                          : "bg-white text-black hover:bg-gray-100"
                      }`}
                    >
                      {pending === deal.opportunity_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : deal.interested ? (
                        <Check className="h-4 w-4" />
                      ) : null}
                      {deal.interested ? "Interest registered — withdraw" : "I'm interested"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
