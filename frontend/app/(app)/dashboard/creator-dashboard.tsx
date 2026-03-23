"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import InstagramCreatorDashboard from "@/components/dashboard/instagram-analytics"
import YouTubeCreatorDashboard from "@/components/dashboard/youtube-analytics"
import CreatorProfileForm from "@/components/dashboard/creator-profile-form"

interface DashboardPageProps {
  userId: number
}

export default function CreatorDashboardPage({ userId }: DashboardPageProps) {
  const [activeTab, setActiveTab] = useState("profile")
  const [profileUpdated, setProfileUpdated] = useState(false)

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Creator Dashboard</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          Manage your social media profiles and view analytics
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="profile" className="flex items-center gap-2">
            <span>👤</span> Profile Setup
          </TabsTrigger>
          <TabsTrigger value="instagram" className="flex items-center gap-2">
            <span>📸</span> Instagram
          </TabsTrigger>
          <TabsTrigger value="youtube" className="flex items-center gap-2">
            <span>▶️</span> YouTube
          </TabsTrigger>
        </TabsList>

        {/* Profile Setup Tab */}
        <TabsContent value="profile" className="space-y-6">
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Creator Profile Setup</h2>
            <p className="text-gray-600 dark:text-gray-400">
              Add your Instagram and YouTube usernames to start tracking your analytics
            </p>
          </div>

          <CreatorProfileForm 
            userId={userId}
            onSuccess={() => {
              setProfileUpdated(true)
              setTimeout(() => setProfileUpdated(false), 3000)
            }}
          />

          {profileUpdated && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
              ✅ Profile updated successfully! Navigate to Instagram or YouTube tabs to scrape data.
            </div>
          )}
        </TabsContent>

        {/* Instagram Tab */}
        <TabsContent value="instagram" className="space-y-6">
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">Instagram Analytics</h2>
            <p className="text-gray-600 dark:text-gray-400">
              View your Instagram profile statistics and post performance
            </p>
          </div>

          <InstagramCreatorDashboard userId={userId} />
        </TabsContent>

        {/* YouTube Tab */}
        <TabsContent value="youtube" className="space-y-6">
          <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold mb-2">YouTube Analytics</h2>
            <p className="text-gray-600 dark:text-gray-400">
              View your YouTube channel statistics and video performance
            </p>
          </div>

          <YouTubeCreatorDashboard userId={userId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
