"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";

type CreatorProfile = {
  id?: number;
  full_name: string;
  location: string;
  primary_platform: string;
  category: string;
  instagram_username?: string;
  instagram_profile_link?: string;
  youtube_username?: string;
  youtube_profile_link?: string;
  bio?: string;
};

export default function CreatorProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<CreatorProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const previousInstagramRef = useRef<string | null>(null);
  const previousYoutubeRef = useRef<string | null>(null);

  // Fetch profile if exists (EDIT MODE)
  useEffect(() => {
    async function fetchProfile() {
      try {
        const res = await api.get("/users/creator-profile");
        setProfile(res.data);
        previousInstagramRef.current = res.data?.instagram_username ?? null;
        previousYoutubeRef.current = res.data?.youtube_username ?? null;
      } catch {
        // Profile doesn't exist → CREATE MODE
        setProfile({
          full_name: "",
          location: "",
          primary_platform: "Instagram",
          category: "",
          instagram_username: "",
          instagram_profile_link: "",
          youtube_username: "",
          youtube_profile_link: "",
          bio: "",
        });
      } finally {
        setLoading(false);
      }
    }

    fetchProfile();
  }, []);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);

    const form = e.currentTarget;

    const payload = {
      full_name: form.full_name.value,
      location: form.location.value,
      primary_platform: form.primary_platform.value,
      category: form.category.value,
      instagram_username: form.instagram_username.value || null,
      instagram_profile_link: form.instagram_profile_link.value || null,
      youtube_username: form.youtube_username.value || null,
      youtube_profile_link: form.youtube_profile_link.value || null,
      bio: form.bio.value || null,
    };

    try {
      let savedProfile: CreatorProfile;

      if (profile?.id) {
        // EDIT
        const res = await api.put("/users/creator-profile", payload);
        savedProfile = res.data;
      } else {
        // CREATE
        const res = await api.post("/users/creator-profile", payload);
        savedProfile = res.data;
      }

      // Trigger scraping for Instagram if username changed or exists
      const newInstagramUsername = savedProfile.instagram_username ?? "";
      const previousInstagramUsername = previousInstagramRef.current ?? "";

      if (
        savedProfile.id &&
        newInstagramUsername &&
        previousInstagramUsername !== newInstagramUsername
      ) {
        try {
          await api.post(`/instagram/scrape/${savedProfile.id}`);
          console.log("Instagram scraping started");
        } catch (scrapeErr) {
          console.warn("Instagram scrape failed:", scrapeErr);
        }
      }

      // Trigger scraping for YouTube if username changed or exists
      const newYoutubeUsername = savedProfile.youtube_username ?? "";
      const previousYoutubeUsername = previousYoutubeRef.current ?? "";

      if (
        savedProfile.id &&
        newYoutubeUsername &&
        previousYoutubeUsername !== newYoutubeUsername
      ) {
        try {
          await api.post(`/youtube/scrape/${savedProfile.id}`);
          console.log("YouTube scraping started");
        } catch (scrapeErr) {
          console.warn("YouTube scrape failed:", scrapeErr);
        }
      }

      setProfile(savedProfile);
      previousInstagramRef.current = newInstagramUsername;
      previousYoutubeRef.current = newYoutubeUsername;

      router.replace("/dashboard/analytics/influencer");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !profile) return null;

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-12">
      <Card className="w-full max-w-2xl p-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">
            {profile.id ? "Edit Creator Profile" : "Complete Creator Profile"}
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Add your Instagram and YouTube information to get started with analytics
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Basic Information</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Full Name *</label>
                <Input
                  name="full_name"
                  defaultValue={profile.full_name}
                  placeholder="Your full name"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Location</label>
                <Input
                  name="location"
                  defaultValue={profile.location}
                  placeholder="City, Country"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Category *</label>
                <Input
                  name="category"
                  defaultValue={profile.category}
                  placeholder="e.g., Fashion, Tech, Gaming"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Primary Platform *
                </label>
                <select
                  name="primary_platform"
                  defaultValue={profile.primary_platform}
                  className="w-full rounded-md border bg-background p-2"
                  required
                >
                  <option value="Instagram">Instagram</option>
                  <option value="YouTube">YouTube</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Bio</label>
              <Textarea
                name="bio"
                defaultValue={profile.bio}
                placeholder="Tell us about yourself"
                rows={3}
              />
            </div>
          </div>

          {/* Instagram Section */}
          <div className="space-y-4 p-4 border rounded-lg bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span>📸</span> Instagram
            </h2>

            <div>
              <label className="block text-sm font-medium mb-2">
                Instagram Username
              </label>
              <Input
                name="instagram_username"
                defaultValue={profile.instagram_username}
                placeholder="username (without @)"
              />
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Enter your Instagram handle
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Instagram Profile Link
              </label>
              <Input
                name="instagram_profile_link"
                defaultValue={profile.instagram_profile_link}
                placeholder="https://instagram.com/username"
              />
            </div>
          </div>

          {/* YouTube Section */}
          <div className="space-y-4 p-4 border rounded-lg bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span>▶️</span> YouTube
            </h2>

            <div>
              <label className="block text-sm font-medium mb-2">
                YouTube Channel Name
              </label>
              <Input
                name="youtube_username"
                defaultValue={profile.youtube_username}
                placeholder="Your channel name"
              />
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Enter your YouTube channel name or handle
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                YouTube Channel Link
              </label>
              <Input
                name="youtube_profile_link"
                defaultValue={profile.youtube_profile_link}
                placeholder="https://youtube.com/@channelname"
              />
            </div>
          </div>

          <Button disabled={saving} className="w-full" size="lg">
            {saving ? "Saving..." : "Save Profile"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
