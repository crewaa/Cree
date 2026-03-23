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

  // Trigger scraping and poll for results
  const handleScrape = async () => {
    setScraping(true)
    try {
      // Remember current scraped_at to detect fresh data
      const previousScrapedAt = data?.profile?.scraped_at

      const response = await api.post(`/instagram/scrape/${userId}`)

      if (response.data.status === "scraping") {
        // Poll for new data every 5 seconds, up to 60 seconds
        const maxAttempts = 12
        let attempt = 0

        const poll = async () => {
          attempt++
          try {
            const pollRes = await api.get(`/instagram/analytics/${userId}`)
            const newData = pollRes.data

            // Check if we got fresh data (different scraped_at or new data where there was none)
            if (
              newData.status === "success" &&
              newData.profile &&
              newData.profile.scraped_at !== previousScrapedAt
            ) {
              setData(newData)
              setScraping(false)
              return
            }
          } catch {
            // Ignore poll errors, keep trying
          }

          if (attempt < maxAttempts) {
            setTimeout(poll, 5000)
          } else {
            // Timed out — fetch whatever is available
            await fetchAnalytics()
            setScraping(false)
          }
        }

        // Start polling after initial 5-second delay
        setTimeout(poll, 5000)
      } else {
        setScraping(false)
      }
    } catch (error) {
      console.error("Failed to trigger scraping:", error)
      setScraping(false)
    }
  }

  // Initial load
  useEffect(() => {
    fetchAnalytics()
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
          {scraping ? "Scraping..." : "Refresh Profile Data"}
        </Button>
      </div>

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
