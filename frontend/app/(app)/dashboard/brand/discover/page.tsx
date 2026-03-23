"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { discoverCreators } from "@/lib/ai"

type RankedCreator = {
  creator_id: string
  creator_name?: string
  fit_level: string
  score_reasoning?: string[]
  risks?: string[]
  recommended_campaign_type?: string
}

type DiscoverResult = {
  ranked_creators: RankedCreator[]
  final_recommendation?: string
}

const NICHE_OPTIONS = [
  "Fitness", "Fashion", "Tech", "Gaming", "Beauty", "Food",
  "Travel", "Lifestyle", "Education", "Finance", "Health",
  "Music", "Comedy", "Sports", "Photography", "Art",
]

export default function DiscoverCreatorsPage() {
  const router = useRouter()

  // Form
  const [niche, setNiche] = useState("")
  const [budgetRange, setBudgetRange] = useState("Mid")
  const [campaignGoal, setCampaignGoal] = useState("Awareness")
  const [targetLocation, setTargetLocation] = useState("India")
  const [platforms, setPlatforms] = useState<string[]>(["instagram"])

  // State
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DiscoverResult | null>(null)
  const [error, setError] = useState("")

  const handlePlatformToggle = (p: string) => {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!niche) return

    setLoading(true)
    setError("")
    setResult(null)

    try {
      const data = await discoverCreators({
        niche,
        budget_range: budgetRange,
        campaign_goal: campaignGoal,
        target_location: targetLocation,
        platform_preferences: platforms,
      })
      setResult(data)
    } catch (err: any) {
      setError(err?.message || "Failed to discover creators. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const fitColors: Record<string, string> = {
    High: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    Medium: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    Low: "bg-red-500/20 text-red-300 border-red-500/30",
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#06070C] text-white">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/15 blur-[160px]" />
        <div className="absolute bottom-[-30%] right-[15%] h-[400px] w-[400px] rounded-full bg-violet-500/10 blur-[140px]" />
      </div>

      <main className="relative z-10 max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <button
          onClick={() => router.back()}
          className="text-gray-400 hover:text-white text-sm mb-8 flex items-center gap-2 transition cursor-pointer"
        >
          ← Back to Brand Studio
        </button>

        <h1 className="text-4xl md:text-5xl font-semibold tracking-tight mb-3">
          Discover Creators
        </h1>
        <p className="text-lg text-gray-400 mb-12">
          Tell us about your campaign and we&apos;ll find the best creators for you.
        </p>

        {/* Form */}
        {!result && !loading && (
          <form onSubmit={handleSubmit} className="space-y-8 max-w-2xl">

            {/* Niche */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                What niche/sector are you targeting? *
              </label>
              <div className="flex flex-wrap gap-2">
                {NICHE_OPTIONS.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setNiche(n)}
                    className={`px-4 py-2 rounded-full text-sm border transition cursor-pointer ${
                      niche === n
                        ? "bg-indigo-500/30 border-indigo-400 text-white"
                        : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={niche}
                onChange={(e) => setNiche(e.target.value)}
                placeholder="Or type a custom niche..."
                className="mt-3 w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50"
              />
            </div>

            {/* Budget */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Budget Range
              </label>
              <div className="flex gap-3">
                {["Low", "Mid", "High"].map((b) => (
                  <button
                    key={b}
                    type="button"
                    onClick={() => setBudgetRange(b)}
                    className={`px-6 py-3 rounded-xl text-sm border transition cursor-pointer ${
                      budgetRange === b
                        ? "bg-indigo-500/30 border-indigo-400 text-white"
                        : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                    }`}
                  >
                    {b === "Low" ? "💰 Low" : b === "Mid" ? "💰💰 Mid" : "💰💰💰 High"}
                  </button>
                ))}
              </div>
            </div>

            {/* Campaign Goal */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Campaign Goal
              </label>
              <div className="flex gap-3">
                {["Awareness", "Sales", "Engagement"].map((g) => (
                  <button
                    key={g}
                    type="button"
                    onClick={() => setCampaignGoal(g)}
                    className={`px-6 py-3 rounded-xl text-sm border transition cursor-pointer ${
                      campaignGoal === g
                        ? "bg-indigo-500/30 border-indigo-400 text-white"
                        : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                    }`}
                  >
                    {g === "Awareness" ? "📢 Awareness" : g === "Sales" ? "🛒 Sales" : "💬 Engagement"}
                  </button>
                ))}
              </div>
            </div>

            {/* Location */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Target Location
              </label>
              <input
                type="text"
                value={targetLocation}
                onChange={(e) => setTargetLocation(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50"
              />
            </div>

            {/* Platform */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-3">
                Platform Preferences
              </label>
              <div className="flex gap-3">
                {["instagram", "youtube"].map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => handlePlatformToggle(p)}
                    className={`px-6 py-3 rounded-xl text-sm border transition cursor-pointer ${
                      platforms.includes(p)
                        ? "bg-indigo-500/30 border-indigo-400 text-white"
                        : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                    }`}
                  >
                    {p === "instagram" ? "📸 Instagram" : "▶️ YouTube"}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-300 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={!niche}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold text-lg hover:from-indigo-500 hover:to-violet-500 transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              🔍 Find Creators
            </button>
          </form>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-24 space-y-6">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-indigo-500/30 rounded-full animate-spin border-t-indigo-500" />
            </div>
            <div className="text-center">
              <p className="text-xl font-medium text-white">AI is analyzing creators...</p>
              <p className="text-gray-400 mt-2">This may take a few seconds</p>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold">
                {result.ranked_creators.length} Creator{result.ranked_creators.length !== 1 ? "s" : ""} Found
              </h2>
              <button
                onClick={() => { setResult(null); setError("") }}
                className="text-sm text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
              >
                ← New Search
              </button>
            </div>

            {result.final_recommendation && (
              <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-200 text-sm">
                💡 {result.final_recommendation}
              </div>
            )}

            <div className="space-y-4">
              {result.ranked_creators.map((creator, i) => (
                <div
                  key={creator.creator_id + i}
                  className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-6 transition-all duration-300 hover:border-white/20"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-xl font-semibold text-white">
                        {creator.creator_name || `Creator ${creator.creator_id}`}
                      </h3>
                      <p className="text-sm text-gray-400 mt-1">
                        ID: {creator.creator_id}
                      </p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${fitColors[creator.fit_level] || fitColors["Low"]}`}>
                      {creator.fit_level} Fit
                    </span>
                  </div>

                  {creator.recommended_campaign_type && (
                    <div className="mb-4">
                      <span className="text-xs text-gray-400">Recommended Campaign</span>
                      <p className="text-sm text-white mt-1">{creator.recommended_campaign_type}</p>
                    </div>
                  )}

                  {creator.score_reasoning && creator.score_reasoning.length > 0 && (
                    <div className="mb-4">
                      <span className="text-xs text-gray-400">Why this creator?</span>
                      <ul className="mt-2 space-y-1">
                        {creator.score_reasoning.map((r, j) => (
                          <li key={j} className="text-sm text-emerald-300/80 flex items-start gap-2">
                            <span className="mt-0.5">✓</span> {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {creator.risks && creator.risks.length > 0 && (
                    <div>
                      <span className="text-xs text-gray-400">Risks</span>
                      <ul className="mt-2 space-y-1">
                        {creator.risks.map((r, j) => (
                          <li key={j} className="text-sm text-amber-300/80 flex items-start gap-2">
                            <span className="mt-0.5">⚠</span> {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {result.ranked_creators.length === 0 && (
              <div className="text-center py-16">
                <p className="text-2xl mb-2">🔍</p>
                <p className="text-gray-400">No creators found matching your criteria.</p>
                <p className="text-gray-500 text-sm mt-1">Try broadening your search parameters.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
