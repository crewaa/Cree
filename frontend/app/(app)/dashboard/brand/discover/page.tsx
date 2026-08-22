"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  BadgeCheck, Instagram, MapPin, Search, Tag, Youtube,
  Megaphone, ShoppingCart, MessageCircle, IndianRupee, Lightbulb, Check, AlertTriangle,
  CalendarDays, SlidersHorizontal, Users,
} from "lucide-react"
import { discoverCreators } from "@/lib/ai"
import { Campaign, listCampaigns } from "@/lib/campaigns"
import { errorMessage } from "@/lib/types"

type RankedCreator = {
  creator_id: string
  creator_name?: string
  fit_level: string
  score_reasoning?: string[]
  risks?: string[]
  recommended_campaign_type?: string
  // Verified profile data, sourced from the database rather than the model.
  category?: string
  location?: string
  primary_platform?: string
  bio?: string
  instagram_username?: string
  instagram_url?: string
  youtube_username?: string
  youtube_url?: string
  followers?: number
  subscribers?: number
  avg_likes?: number
  avg_comments?: number
  engagement_rate?: number
  is_verified?: boolean
}

/** 142500 -> "142.5K" */
function compact(n?: number): string {
  if (n === undefined || n === null) return "—"
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

type DiscoverResult = {
  ranked_creators: RankedCreator[]
  final_recommendation?: string
  campaign_id?: number | null
  campaign_name?: string | null
  criteria_source?: "campaign" | "custom"
  follower_floor_relaxed?: boolean
}

const NICHE_OPTIONS = [
  "Fitness", "Fashion", "Tech", "Gaming", "Beauty", "Food",
  "Travel", "Lifestyle", "Education", "Finance", "Health",
  "Music", "Comedy", "Sports", "Photography", "Art",
]

export default function DiscoverCreatorsPage() {
  const router = useRouter()

  // Campaigns to search against. A brand that has already stated its brief
  // should not have to restate it here — that duplication was the last place
  // the two halves of the product could disagree about the same campaign.
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [campaignsLoading, setCampaignsLoading] = useState(true)
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(null)
  const [customMode, setCustomMode] = useState(false)

  // Ad-hoc form
  const [niche, setNiche] = useState("")
  const [budgetRange, setBudgetRange] = useState("Mid")
  const [campaignGoal, setCampaignGoal] = useState("Awareness")
  const [targetLocation, setTargetLocation] = useState("India")
  const [platforms, setPlatforms] = useState<string[]>(["instagram"])

  // State
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DiscoverResult | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    let cancelled = false

    listCampaigns()
      .then((all) => {
        if (cancelled) return
        const open = all.filter((c) => c.status !== "closed")
        setCampaigns(open)
        // Preselect when there is exactly one — with a single campaign there is
        // nothing to choose between, and an unselected radio is just friction.
        if (open.length === 1) setSelectedCampaignId(open[0].id)
        if (open.length === 0) setCustomMode(true)
      })
      .catch(() => {
        // Campaigns are an enhancement here, not a prerequisite. If the list
        // cannot be loaded, fall back to the ad-hoc form rather than blocking
        // discovery entirely.
        if (!cancelled) setCustomMode(true)
      })
      .finally(() => {
        if (!cancelled) setCampaignsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const selectedCampaign = campaigns.find((c) => c.id === selectedCampaignId) ?? null
  const canSubmit = customMode ? Boolean(niche) : Boolean(selectedCampaign)

  const handlePlatformToggle = (p: string) => {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    setLoading(true)
    setError("")
    setResult(null)

    try {
      const data = await discoverCreators(
        customMode || !selectedCampaign
          ? {
              niche,
              budget_range: budgetRange,
              campaign_goal: campaignGoal,
              target_location: targetLocation,
              platform_preferences: platforms,
            }
          : { campaign_id: selectedCampaign.id }
      )
      setResult(data)
    } catch (err) {
      setError(errorMessage(err, "Failed to discover creators. Please try again."))
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
    <div className="relative overflow-hidden">
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
          Pick a campaign and we&apos;ll rank creators against its brief.
        </p>

        {/* Form */}
        {!result && !loading && (
          <form onSubmit={handleSubmit} className="space-y-8 max-w-2xl">

            {/* Which campaign are we searching for? */}
            {!campaignsLoading && campaigns.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Search for
                </label>
                <div className="space-y-3">
                  {campaigns.map((c) => {
                    const active = !customMode && selectedCampaignId === c.id
                    return (
                      <button
                        key={c.id}
                        type="button"
                        aria-pressed={active}
                        onClick={() => { setCustomMode(false); setSelectedCampaignId(c.id) }}
                        className={`w-full rounded-xl border p-4 text-left transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${
                          active
                            ? "bg-indigo-500/20 border-indigo-400"
                            : "bg-white/5 border-white/10 hover:border-white/30"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-white">{c.name}</span>
                          {c.budget_per_creator != null && (
                            <span className="shrink-0 text-sm text-gray-300">
                              {c.currency === "INR" ? "₹" : `${c.currency} `}
                              {c.budget_per_creator.toLocaleString()}
                            </span>
                          )}
                        </div>
                        {/* The criteria the search will actually use — shown so
                            the brand never has to trust that it matched. */}
                        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-400">
                          <span className="flex items-center gap-1">
                            <Tag className="h-3.5 w-3.5" /> {c.niche}
                          </span>
                          <span className="flex items-center gap-1">
                            <Megaphone className="h-3.5 w-3.5" /> {c.campaign_goal}
                          </span>
                          {c.target_location && (
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3.5 w-3.5" /> {c.target_location}
                            </span>
                          )}
                          {c.min_followers != null && c.min_followers > 0 && (
                            <span className="flex items-center gap-1">
                              <Users className="h-3.5 w-3.5" /> {compact(c.min_followers)}+ followers
                            </span>
                          )}
                          {c.deadline && (
                            <span className="flex items-center gap-1">
                              <CalendarDays className="h-3.5 w-3.5" />
                              {new Date(c.deadline).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </button>
                    )
                  })}

                  <button
                    type="button"
                    aria-pressed={customMode}
                    onClick={() => setCustomMode(true)}
                    className={`w-full rounded-xl border p-4 text-left transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${
                      customMode
                        ? "bg-indigo-500/20 border-indigo-400"
                        : "bg-white/5 border-white/10 hover:border-white/30"
                    }`}
                  >
                    <span className="flex items-center gap-2 font-medium text-white">
                      <SlidersHorizontal className="h-4 w-4" /> Something else
                    </span>
                    <p className="mt-1 text-sm text-gray-400">
                      Search on one-off criteria without saving a campaign.
                    </p>
                  </button>
                </div>

                {!customMode && !selectedCampaign && (
                  <p className="mt-3 text-sm text-gray-500">
                    Choose which campaign to match against.
                  </p>
                )}

                {!customMode && selectedCampaign && (
                  <p className="mt-3 text-sm text-gray-500">
                    Matching against this campaign&apos;s own brief — nothing to re-enter.{" "}
                    <Link
                      href="/dashboard/brand/campaigns"
                      className="text-indigo-400 transition hover:text-indigo-300"
                    >
                      Edit campaign
                    </Link>
                  </p>
                )}
              </div>
            )}

            {!campaignsLoading && campaigns.length === 0 && (
              <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-gray-400">
                Searching on one-off criteria.{" "}
                <Link
                  href="/dashboard/brand/campaigns"
                  className="text-indigo-400 transition hover:text-indigo-300"
                >
                  Create a campaign
                </Link>{" "}
                to search against a real brief and let creators apply to it.
              </div>
            )}

            {customMode && (
            <div className="space-y-8">

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
                    <span className="flex items-center gap-1.5">
                      <span className="flex" aria-hidden="true">
                        {Array.from({ length: b === "Low" ? 1 : b === "Mid" ? 2 : 3 }).map((_, i) => (
                          <IndianRupee key={i} className="h-3.5 w-3.5" />
                        ))}
                      </span>
                      {b}
                    </span>
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
                    <span className="flex items-center gap-2">
                      {g === "Awareness" ? <Megaphone className="h-4 w-4" />
                        : g === "Sales" ? <ShoppingCart className="h-4 w-4" />
                        : <MessageCircle className="h-4 w-4" />}
                      {g}
                    </span>
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
                    <span className="flex items-center gap-2">
                      {p === "instagram" ? <Instagram className="h-4 w-4" /> : <Youtube className="h-4 w-4" />}
                      {p === "instagram" ? "Instagram" : "YouTube"}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            </div>
            )}

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-300 text-sm">
                {error}
              </div>
            )}

            {/* The label carries the reason it is disabled. With more than one
                campaign nothing is preselected — choosing for the brand risks
                running a search against the wrong brief — but a greyed-out
                button with no explanation reads as broken. */}
            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold text-lg hover:from-indigo-500 hover:to-violet-500 transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <span className="flex items-center justify-center gap-2">
                <Search className="h-5 w-5" />
                {canSubmit
                  ? "Find Creators"
                  : customMode
                    ? "Pick a niche to continue"
                    : "Pick a campaign to continue"}
              </span>
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
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold">
                  {result.ranked_creators.length} Creator{result.ranked_creators.length !== 1 ? "s" : ""} Found
                </h2>
                {/* Which criteria produced this — so a shortlist is never
                    mistaken for one built against a different campaign. */}
                <p className="mt-1 text-sm text-gray-400">
                  {result.criteria_source === "campaign" && result.campaign_name
                    ? `Matched against ${result.campaign_name}`
                    : "Matched against one-off criteria"}
                </p>
              </div>
              <button
                onClick={() => { setResult(null); setError("") }}
                className="shrink-0 text-sm text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
              >
                ← New Search
              </button>
            </div>

            {result.final_recommendation && (
              <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-200 text-sm">
                <span className="flex items-start gap-2">
                  <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  {result.final_recommendation}
                </span>
              </div>
            )}

            <div className="space-y-4">
              {result.ranked_creators.map((creator, i) => (
                <div
                  key={creator.creator_id + i}
                  className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-6 transition-all duration-300 hover:border-white/20"
                >
                  {/* Identity — the raw database id used to be printed here */}
                  <div className="flex items-start justify-between mb-4 gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-xl font-semibold text-white">
                          {creator.creator_name || "Creator"}
                        </h3>
                        {creator.is_verified && (
                          <BadgeCheck
                            className="h-4 w-4 text-sky-400"
                            aria-label="Verified account"
                          />
                        )}
                      </div>

                      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-400">
                        {creator.category && (
                          <span className="flex items-center gap-1">
                            <Tag className="h-3.5 w-3.5" /> {creator.category}
                          </span>
                        )}
                        {creator.location && (
                          <span className="flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5" /> {creator.location}
                          </span>
                        )}
                      </div>

                      {creator.bio && (
                        <p className="mt-2 text-sm text-gray-400 line-clamp-2">{creator.bio}</p>
                      )}
                    </div>

                    <span className={`shrink-0 px-3 py-1 rounded-full text-xs font-medium border ${fitColors[creator.fit_level] || fitColors["Low"]}`}>
                      {creator.fit_level} Fit
                    </span>
                  </div>

                  {/* Audience — what a brand actually needs to decide */}
                  <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {creator.followers != null && (
                      <Metric label="Followers" value={compact(creator.followers)} />
                    )}
                    {creator.subscribers != null && (
                      <Metric label="Subscribers" value={compact(creator.subscribers)} />
                    )}
                    {creator.engagement_rate != null && (
                      <Metric label="Engagement" value={`${creator.engagement_rate}%`} />
                    )}
                    {creator.avg_likes != null && (
                      <Metric label="Avg likes" value={compact(creator.avg_likes)} />
                    )}
                  </div>

                  {/* Where to find them */}
                  {(creator.instagram_url || creator.youtube_url) && (
                    <div className="mb-4 flex flex-wrap gap-2">
                      {creator.instagram_url && (
                        <a
                          href={creator.instagram_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-gray-300 transition hover:border-white/25 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                        >
                          <Instagram className="h-3.5 w-3.5" />
                          @{creator.instagram_username}
                        </a>
                      )}
                      {creator.youtube_url && (
                        <a
                          href={creator.youtube_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-gray-300 transition hover:border-white/25 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                        >
                          <Youtube className="h-3.5 w-3.5" />
                          {creator.youtube_username}
                        </a>
                      )}
                    </div>
                  )}

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
                            <Check className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {r}
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
                            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {r}
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
                <Search className="mx-auto mb-3 h-8 w-8 text-gray-600" aria-hidden="true" />
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

/** Small labelled stat used on the discovery cards. */
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-white">{value}</p>
    </div>
  )
}
