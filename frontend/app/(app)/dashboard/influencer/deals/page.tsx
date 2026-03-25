"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { getBrandDeals, getCachedBrandDeals } from "@/lib/ai"

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
}

type DealsResponse = {
  opportunities: BrandDeal[]
  total: number
}

export default function BrandDealsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [deals, setDeals] = useState<DealsResponse | null>(null)
  const [error, setError] = useState("")

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
    setLoading(true)
    setError("")
    try {
      const data = await getBrandDeals()
      setDeals(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load brand deals. Please try again.")
    } finally {
      setLoading(false)
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
    <div className="relative min-h-screen overflow-hidden bg-[#06070C] text-white">
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

        {/* Loading */}
        {loading && (
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
        {!loading && !deals && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-6">
            <p className="text-5xl">🏷️</p>
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
              ✦ Find My Deals
            </button>
          </div>
        )}

        {/* Results */}
        {!loading && !error && deals && (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold">
                {deals.total} {deals.total === 1 ? "Opportunity" : "Opportunities"} Available
              </h2>
              <button
                onClick={fetchDeals}
                className="text-sm text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
              >
                🔄 Refresh
              </button>
            </div>

            {deals.total === 0 ? (
              <div className="text-center py-16">
                <p className="text-4xl mb-4">🏷️</p>
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

                    {/* Compensation & Timeline */}
                    <div className="grid grid-cols-2 gap-4 mb-3">
                      {deal.compensation && (
                        <div>
                          <span className="text-xs text-gray-500 uppercase tracking-wide">Compensation</span>
                          <p className="text-sm text-emerald-300 mt-1 font-medium">{deal.compensation}</p>
                        </div>
                      )}
                      {deal.timeline && (
                        <div>
                          <span className="text-xs text-gray-500 uppercase tracking-wide">Timeline</span>
                          <p className="text-sm text-gray-300 mt-1">{deal.timeline}</p>
                        </div>
                      )}
                    </div>

                    {/* Deliverables */}
                    {deal.deliverables && deal.deliverables.length > 0 && (
                      <div>
                        <span className="text-xs text-gray-500 uppercase tracking-wide">Deliverables</span>
                        <ul className="mt-2 space-y-1">
                          {deal.deliverables.map((d, j) => (
                            <li key={j} className="text-sm text-gray-300 flex items-start gap-2">
                              <span className="mt-0.5 text-indigo-400">•</span> {d}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
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
