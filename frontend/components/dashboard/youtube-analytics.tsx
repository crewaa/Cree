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
      const response = await api.post(`/youtube/scrape/${userId}`)
      
      if (response.data.status === "scraping") {
        // Scraping started in background, wait a bit then fetch
        setTimeout(() => {
          fetchAnalytics()
          setScraping(false)
        }, 3000)
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
          {scraping ? "Scraping..." : "Refresh Channel Data"}
        </Button>
      </div>

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
