"use client"

import { useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/axios"
import ProfileHeader from "./profileheader"
import ChartCard from "./chartwrapper"
import Stat from "./statcard"
import LineChartComponent from "./linechartcomponent"
import RecentPosts from "./recentposts"

interface YouTubeChannel {
  id: number
  channel_id: string
  username: string
  title: string
  description: string
  profile_picture: string
  subscribers: number
  total_views: number
  total_videos: number
  is_verified: boolean
  scraped_at: string
}

interface YouTubeVideo {
  id: number
  video_id: string
  title: string
  description: string
  thumbnail: string
  views: number
  likes: number
  comments: number
  duration: number
  published_at: string
  scraped_at: string
}

interface YouTubeAnalyticsResponse {
  status: "success" | "no_data" | "error"
  message?: string
  channel: YouTubeChannel | null
  videos: YouTubeVideo[]
}

export default function YouTubeCreatorDashboard({ userId }: { userId: number }) {
  const [data, setData] = useState<YouTubeAnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [scraping, setScraping] = useState(false)
  const [scrapeError, setScrapeError] = useState<string | null>(null)

  // Fetch analytics data
  const fetchAnalytics = async () => {
    setLoading(true)
    try {
      const response = await api.get(`/youtube/analytics/${userId}`)
      setData(response.data)
    } catch (error) {
      console.error("Failed to fetch analytics:", error)
      setData({
        status: "error",
        message: "Failed to fetch analytics data",
        channel: null,
        videos: []
      })
    } finally {
      setLoading(false)
    }
  }

  // Trigger scraping
  const handleScrape = async () => {
    setScraping(true)
    try {
      await api.post(`/youtube/scrape/${userId}`)

      // Poll the job record instead of blindly waiting 3 seconds and hoping.
      const maxAttempts = 24 // ~2 minutes
      let attempt = 0

      const poll = async () => {
        attempt++
        try {
          const statusRes = await api.get(`/youtube/scrape-status/${userId}`)
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
        const response = await api.get(`/youtube/analytics/${userId}`)
        if (!cancelled) setData(response.data)
      } catch (error) {
        console.error("Failed to fetch analytics:", error)
        if (!cancelled) setData({
        status: "error",
        message: "Failed to fetch analytics data",
        channel: null,
        videos: []
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
    if (!data?.channel || data.videos.length === 0) return null

    const totalViews = data.videos.reduce((a, b) => a + b.views, 0)
    const totalLikes = data.videos.reduce((a, b) => a + b.likes, 0)
    const avgEngagement = (
      ((totalLikes) / (totalViews || 1)) * 100
    ).toFixed(2)

    return {
      avgViews: Math.round(totalViews / data.videos.length),
      avgLikes: Math.round(totalLikes / data.videos.length),
      engagement: avgEngagement,
    }
  }, [data])

  if (loading) {
    return <p className="text-center py-8">Loading YouTube dashboard…</p>
  }

  if (!data?.channel) {
    return (
      <div className="text-center py-8 space-y-4">
        <p className="text-gray-500">{data?.message || "No YouTube channel data found"}</p>
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
          className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800"
        >
          {scraping ? "Scraping..." : "Scrape YouTube Channel"}
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
          className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800"
        >
          {scraping ? "Importing…" : "Refresh Channel Data"}
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

      {/* Channel Header */}
      <ProfileHeader 
        profile={{
          full_name: data.channel.title,
          username: data.channel.username,
          profile_picture: data.channel.profile_picture,
          bio: data.channel.description,
          is_verified: data.channel.is_verified,
          scraped_at: data.channel.scraped_at,
        }}
      />

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Subscribers" value={data.channel.subscribers.toLocaleString()} />
        <Stat label="Total Views" value={data.channel.total_views.toLocaleString()} />
        <Stat label="Videos" value={data.channel.total_videos} />
        <Stat label="Avg Engagement %" value={stats?.engagement ? `${stats.engagement}%` : "N/A"} />
      </div>

      {/* Charts */}
      {data.videos.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <ChartCard title="Views Over Time">
            <LineChartComponent data={data.videos} dataKey="views" />
          </ChartCard>

          <ChartCard title="Likes Over Time">
            <LineChartComponent data={data.videos} dataKey="likes" />
          </ChartCard>
        </div>
      )}

      {/* Recent Videos */}
      {data.videos.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">Recent Videos</h3>
          <div className="space-y-4">
            {data.videos.slice(0, 5).map((video) => (
              <div key={video.id} className="flex gap-4 p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800">
                <img 
                  src={video.thumbnail} 
                  alt={video.title}
                  className="w-24 h-16 object-cover rounded"
                />
                <div className="flex-1">
                  <h4 className="font-semibold line-clamp-2">{video.title}</h4>
                  <p className="text-sm text-gray-500 mt-2">
                    {video.views.toLocaleString()} views • {video.likes.toLocaleString()} likes • {video.comments} comments
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Published: {new Date(video.published_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Last Updated */}
      <div className="text-sm text-gray-500 text-center">
        Last updated: {new Date(data.channel.scraped_at).toLocaleString()}
      </div>
    </div>
  )
}
