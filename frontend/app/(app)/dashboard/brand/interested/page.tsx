"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowLeft, Inbox, Instagram, Loader2, Mail, MapPin, Tag, Youtube,
} from "lucide-react"

import { getInterestedCreators } from "@/lib/ai"
import { errorMessage } from "@/lib/types"

interface InterestedCreator {
  interest_id: number
  creator_id: number
  creator_name?: string
  email: string
  category?: string
  location?: string
  instagram_username?: string
  youtube_username?: string
  followers?: number
  engagement_rate?: number
  message?: string
  campaign_type?: string
  created_at: string
}

function compact(n?: number): string {
  if (n === undefined || n === null) return "—"
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

/**
 * Creators who responded to this brand's opportunities.
 *
 * This is the other half of the loop: the brand never learns who saw an
 * opportunity, only who chose to raise their hand. Contact details appear here
 * because the creator opted in by expressing interest.
 */
export default function InterestedCreatorsPage() {
  const router = useRouter()
  const [creators, setCreators] = useState<InterestedCreator[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    async function load() {
      try {
        const data = await getInterestedCreators()
        setCreators(data.creators ?? [])
      } catch (err) {
        setError(errorMessage(err, "Could not load interested creators."))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/15 blur-[160px]" />
      </div>

      <main className="relative z-10 mx-auto max-w-5xl px-6 py-12">
        <button
          onClick={() => router.push("/dashboard/brand")}
          className="mb-8 flex items-center gap-2 text-sm text-gray-400 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Brand Studio
        </button>

        <h1 className="mb-3 text-4xl font-semibold tracking-tight md:text-5xl">
          Interested Creators
        </h1>
        <p className="mb-10 text-lg text-gray-400">
          Creators who responded to your campaign opportunities.
        </p>

        {loading && (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            <span className="sr-only">Loading…</span>
          </div>
        )}

        {error && !loading && (
          <p
            role="alert"
            className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300"
          >
            {error}
          </p>
        )}

        {!loading && !error && creators.length === 0 && (
          <div className="py-20 text-center">
            <Inbox className="mx-auto mb-4 h-10 w-10 text-gray-600" aria-hidden="true" />
            <p className="text-xl text-gray-400">No responses yet</p>
            <p className="mt-2 text-sm text-gray-500">
              Creators who are interested in your opportunities will appear here with
              their contact details.
            </p>
          </div>
        )}

        {!loading && creators.length > 0 && (
          <div className="space-y-4">
            {creators.map((c) => (
              <div
                key={c.interest_id}
                className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-6 transition hover:border-white/20"
              >
                <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h2 className="text-xl font-semibold text-white">
                      {c.creator_name || "Creator"}
                    </h2>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-gray-400">
                      {c.category && (
                        <span className="flex items-center gap-1">
                          <Tag className="h-3.5 w-3.5" /> {c.category}
                        </span>
                      )}
                      {c.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3.5 w-3.5" /> {c.location}
                        </span>
                      )}
                    </div>
                  </div>

                  {c.campaign_type && (
                    <span className="shrink-0 rounded-full border border-indigo-500/30 bg-indigo-500/15 px-3 py-1 text-xs text-indigo-300">
                      {c.campaign_type}
                    </span>
                  )}
                </div>

                <div className="mb-4 flex flex-wrap gap-6 text-sm">
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-gray-500">Followers</p>
                    <p className="mt-0.5 font-medium text-white">{compact(c.followers)}</p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-gray-500">Engagement</p>
                    <p className="mt-0.5 font-medium text-white">
                      {c.engagement_rate != null ? `${c.engagement_rate}%` : "—"}
                    </p>
                  </div>
                </div>

                {c.message && (
                  <blockquote className="mb-4 border-l-2 border-white/15 pl-4 text-sm italic text-gray-300">
                    “{c.message}”
                  </blockquote>
                )}

                <div className="flex flex-wrap gap-2">
                  <a
                    href={`mailto:${c.email}`}
                    className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-sm font-medium text-black transition hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
                  >
                    <Mail className="h-3.5 w-3.5" /> {c.email}
                  </a>
                  {c.instagram_username && (
                    <a
                      href={`https://instagram.com/${c.instagram_username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300 transition hover:border-white/25 hover:text-white"
                    >
                      <Instagram className="h-3.5 w-3.5" /> @{c.instagram_username}
                    </a>
                  )}
                  {c.youtube_username && (
                    <a
                      href={`https://youtube.com/@${c.youtube_username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300 transition hover:border-white/25 hover:text-white"
                    >
                      <Youtube className="h-3.5 w-3.5" /> {c.youtube_username}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
