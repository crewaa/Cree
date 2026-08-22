"use client"

import { useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/axios"
import ProfileHeader from "./profileheader"
import ChartCard from "./chartwrapper"
import Stat from "./statcard"
import LineChartComponent from "./linechartcomponent"
import RecentPosts from "./recentposts"

interface InstagramProfile {
  id: number
  full_name: string
  username: string
  profile_picture: string
  followers: number
  following: number
  posts_count: number
  bio: string
  is_verified: boolean
  scraped_at: string
}

interface InstagramPost {
  id: number
  shortcode: string
  likes: number
  comments: number
  views: number | null
  caption: string
  posted_at: string
  is_video: boolean
  scraped_at: string
}

interface InstagramAnalyticsResponse {
  status: "success" | "no_data" | "error"
  message?: string
  profile: InstagramProfile | null
  posts: InstagramPost[]
}

export default function InstagramCreatorDashboard({ userId }: { userId: number }) {
  const [data, setData] = useState<InstagramAnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [scraping, setScraping] = useState(false)
  const [scrapeError, setScrapeError] = useState<string | null>(null)

  // Fetch analytics data
  const fetchAnalytics = async () => {
    setLoading(true)
    try {
      const response = await api.get(`/instagram/analytics/${userId}`)
      setData(response.data)
    } catch (error) {
      console.error("Failed to fetch analytics:", error)
      setData({
        status: "error",
        message: "Failed to fetch analytics data",
        profile: null,
        posts: []
      })
    } finally {
      setLoading(false)
    }
  }

  // Trigger scraping, then poll the job status rather than guessing from data.
  //
  // Previously this polled the analytics endpoint and compared scraped_at,
  // which could not tell "still running" from "failed" — a failed scrape just
  // timed out after 60s and left an empty dashboard with no explanation.
  const handleScrape = async () => {
    setScraping(true)
    setScrapeError(null)
    try {
      await api.post(`/instagram/scrape/${userId}`)

      const maxAttempts = 24 // ~2 minutes
      let attempt = 0

      const poll = async () => {
        attempt++
        try {
          const statusRes = await api.get(`/instagram/scrape-status/${userId}`)
          const job = statusRes.data

          if (job.status === "success") {
            await fetchAnalytics()
            setScraping(false)
            return
          }

          if (job.status === "error") {
            setScrapeError(job.message || "The import failed. Please try again.")
            setScraping(false)
            return
          }
        } catch {
          // Transient poll failure — keep trying.
        }

        if (attempt < maxAttempts) {
          setTimeout(poll, 5000)
        } else {
          await fetchAnalytics()
          setScrapeError(
            "This is taking longer than expected. Your data will appear here once the import finishes."
          )
          setScraping(false)
        }
      }

      setTimeout(poll, 3000)
    } catch (error) {
      setScrapeError(
        error instanceof Error ? error.message : "Could not start the import."
      )
      setScraping(false)
    }
  }

  // Loads on mount and whenever the creator changes.
  //
  // The fetch is inlined and guarded rather than calling `fetchAnalytics()`
  // directly: that set `loading` synchronously during the effect, which costs an
  // extra render pass, and it could also write state after the component had
  // unmounted. `loading` already starts true, so the initial spinner is
  // unaffected.
  useEffect(() => {
    let cancelled = false

    ;(async () => {
      try {
        const response = await api.get(`/instagram/analytics/${userId}`)
        if (!cancelled) setData(response.data)
      } catch (error) {
        console.error("Failed to fetch analytics:", error)
        if (!cancelled) setData({
        status: "error",
        message: "Failed to fetch analytics data",
        profile: null,
        posts: []
      })
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [userId])

  const stats = useMemo(() => {
    if (!data?.profile || data.posts.length === 0) return null

    const totalLikes = data.posts.reduce((a, b) => a + b.likes, 0)
    const totalComments = data.posts.reduce((a, b) => a + b.comments, 0)

    return {
      avgLikes: Math.round(totalLikes / data.posts.length),
      avgComments: Math.round(totalComments / data.posts.length),
      engagementRate: (
        ((totalLikes + totalComments) /
          (data.profile.followers * data.posts.length)) *
        100
      ).toFixed(2),
    }
  }, [data])

  if (loading) {
    return <p className="text-center py-8">Loading creator dashboard…</p>
  }

  if (!data?.profile) {
    return (
      <div className="text-center py-8 space-y-4">
        <p className="text-gray-500">{data?.message || "No Instagram profile data found"}</p>
      {scrapeError && (
        <p
          role="alert"
          className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-300"
        >
          {scrapeError}
        </p>
      )}
        <Button 
          onClick={handleScrape} 
          disabled={scraping}
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
        >
          {scraping ? "Scraping..." : "Scrape Instagram Profile"}
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Scrape Button */}
      <div className="flex justify-end">
        <Button
          onClick={handleScrape}
          disabled={scraping}
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
        >
          {scraping ? "Importing…" : "Refresh Profile Data"}
        </Button>
      </div>

      {scrapeError && (
        <p
          role="alert"
          className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-300"
        >
          {scrapeError}
        </p>
      )}

      {/* Profile Header */}
      <ProfileHeader profile={data.profile} />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Followers" value={data.profile.followers.toLocaleString()} />
        <Stat label="Posts" value={data.profile.posts_count} />
        <Stat label="Avg Likes" value={stats?.avgLikes ?? 0} />
        <Stat label="Engagement %" value={stats?.engagementRate ? `${stats.engagementRate}%` : "N/A"} />
      </div>

      {/* Charts */}
      {data.posts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ChartCard title="Likes Over Time">
            <LineChartComponent data={data.posts} dataKey="likes" />
          </ChartCard>

          <ChartCard title="Comments Over Time">
            <LineChartComponent data={data.posts} dataKey="comments" />
          </ChartCard>
        </div>
      )}

      {/* Recent Posts */}
      {data.posts.length > 0 && <RecentPosts posts={data.posts} />}

      {/* Last Updated */}
      <div className="text-sm text-gray-500 text-center">
        Last updated: {new Date(data.profile.scraped_at).toLocaleString()}
      </div>
    </div>
  )
}
