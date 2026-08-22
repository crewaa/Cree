"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import InstagramAnalytics from "@/components/dashboard/instagram-analytics";
import YouTubeAnalytics from "@/components/dashboard/youtube-analytics";
import { CurrentUser } from "@/lib/types"
import { Instagram, Youtube } from "lucide-react";

export default function Analytics() {
  const { user } = useSession();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("instagram");


  if (!user) return null;

  return (
    <main className="flex-1 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Track your social media performance and growth
          </p>
        </div>
        <Button
          onClick={() => router.push("/dashboard/profile")}
          variant="outline"
        >
          Edit Profile
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="instagram" className="flex items-center gap-2">
            <Instagram className="h-4 w-4" />
            <span>Instagram</span>
          </TabsTrigger>
          <TabsTrigger value="youtube" className="flex items-center gap-2">
            <Youtube className="h-4 w-4" />
            <span>YouTube</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="instagram" className="space-y-6">
          <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold">Instagram Analytics</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              View your Instagram profile statistics and post performance
            </p>
          </div>
          <InstagramAnalytics userId={user.id} />
        </TabsContent>

        <TabsContent value="youtube" className="space-y-6">
          <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 p-6 rounded-lg">
            <h2 className="text-2xl font-semibold">YouTube Analytics</h2>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              View your YouTube channel statistics and video performance
            </p>
          </div>
          <YouTubeAnalytics userId={user.id} />
        </TabsContent>
      </Tabs>
    </main>
  );
}