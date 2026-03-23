"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/axios"

type BrandProfile = {
  id?: number
  brand_name: string
  industry: string
  description?: string
  website?: string
  logo_url?: string
  campaign_goal: string
  budget_range: string
  target_location?: string
  target_languages?: string
  platform_preferences?: string
}

const INDUSTRY_OPTIONS = [
  "Fitness & Nutrition", "Fashion & Beauty", "Technology", "Gaming",
  "Food & Beverage", "Travel & Tourism", "Education", "Finance",
  "Health & Wellness", "E-commerce", "SaaS", "Entertainment",
]

export default function BrandProfilePage() {
  const router = useRouter()
  const [profile, setProfile] = useState<BrandProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    async function fetchProfile() {
      try {
        const res = await api.get("/users/brand-profile")
        setProfile(res.data)
      } catch {
        // No profile → create mode
        setProfile({
          brand_name: "",
          industry: "",
          description: "",
          website: "",
          logo_url: "",
          campaign_goal: "Awareness",
          budget_range: "Mid",
          target_location: "",
          target_languages: "[]",
          platform_preferences: "[]",
        })
      } finally {
        setLoading(false)
      }
    }
    fetchProfile()
  }, [])

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setSaving(true)

    const form = e.currentTarget

    const payload = {
      brand_name: form.brand_name.value,
      industry: form.industry_field.value,
      description: form.description.value || null,
      website: form.website.value || null,
      campaign_goal: form.campaign_goal.value,
      budget_range: form.budget_range.value,
      target_location: form.target_location.value || null,
      target_languages: JSON.stringify(
        form.target_languages.value ? form.target_languages.value.split(",").map((s: string) => s.trim()) : []
      ),
      platform_preferences: JSON.stringify(
        [
          form.pref_instagram.checked && "instagram",
          form.pref_youtube.checked && "youtube",
        ].filter(Boolean)
      ),
    }

    try {
      if (profile?.id) {
        await api.put("/users/brand-profile", payload)
      } else {
        await api.post("/users/brand-profile", payload)
      }
      router.replace("/dashboard/brand")
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Failed to save profile")
    } finally {
      setSaving(false)
    }
  }

  if (loading || !profile) return null

  const existingPlatforms: string[] = (() => {
    try {
      return JSON.parse(profile.platform_preferences || "[]")
    } catch {
      return []
    }
  })()

  const existingLanguages: string[] = (() => {
    try {
      return JSON.parse(profile.target_languages || "[]")
    } catch {
      return []
    }
  })()

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#06070C] text-white">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-cyan-500/15 blur-[160px]" />
        <div className="absolute bottom-[-30%] right-[15%] h-[400px] w-[400px] rounded-full bg-indigo-500/10 blur-[140px]" />
      </div>

      <main className="relative z-10 flex min-h-screen items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-8 space-y-6">
          <div>
            <h1 className="text-2xl font-bold">
              {profile.id ? "Edit Brand Profile" : "Setup Brand Profile"}
            </h1>
            <p className="text-sm text-gray-400 mt-2">
              Tell us about your brand so AI can find the best creators for you.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Brand Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Brand Name *</label>
              <input
                name="brand_name"
                defaultValue={profile.brand_name}
                required
                placeholder="Your brand name"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50"
              />
            </div>

            {/* Industry */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Industry *</label>
              <select
                name="industry_field"
                defaultValue={profile.industry}
                required
                className="w-full bg-[#0E1220] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/50"
              >
                <option value="">Select industry</option>
                {INDUSTRY_OPTIONS.map((i) => (
                  <option key={i} value={i}>{i}</option>
                ))}
              </select>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
              <textarea
                name="description"
                defaultValue={profile.description}
                rows={3}
                placeholder="Tell us about your brand"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 resize-none"
              />
            </div>

            {/* Website */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Website</label>
              <input
                name="website"
                defaultValue={profile.website}
                placeholder="https://yourbrand.com"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50"
              />
            </div>

            {/* Campaign Goal & Budget */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Campaign Goal</label>
                <select
                  name="campaign_goal"
                  defaultValue={profile.campaign_goal}
                  className="w-full bg-[#0E1220] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="Awareness">📢 Awareness</option>
                  <option value="Sales">🛒 Sales</option>
                  <option value="Engagement">💬 Engagement</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Budget Range</label>
                <select
                  name="budget_range"
                  defaultValue={profile.budget_range}
                  className="w-full bg-[#0E1220] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="Low">💰 Low</option>
                  <option value="Mid">💰💰 Mid</option>
                  <option value="High">💰💰💰 High</option>
                </select>
              </div>
            </div>

            {/* Target Location */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Target Location</label>
              <input
                name="target_location"
                defaultValue={profile.target_location}
                placeholder="e.g., India, US, Global"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50"
              />
            </div>

            {/* Target Languages */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Target Languages</label>
              <input
                name="target_languages"
                defaultValue={existingLanguages.join(", ")}
                placeholder="English, Hindi"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50"
              />
              <p className="text-xs text-gray-500 mt-1">Separate multiple languages with commas</p>
            </div>

            {/* Platform Preferences */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Platform Preferences</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    name="pref_instagram"
                    defaultChecked={existingPlatforms.includes("instagram")}
                    className="accent-indigo-500"
                  />
                  <span className="text-sm text-gray-300">📸 Instagram</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    name="pref_youtube"
                    defaultChecked={existingPlatforms.includes("youtube")}
                    className="accent-indigo-500"
                  />
                  <span className="text-sm text-gray-300">▶️ YouTube</span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-cyan-600 to-indigo-600 text-white font-semibold text-lg hover:from-cyan-500 hover:to-indigo-500 transition disabled:opacity-40 cursor-pointer"
            >
              {saving ? "Saving..." : "Save Brand Profile"}
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}
