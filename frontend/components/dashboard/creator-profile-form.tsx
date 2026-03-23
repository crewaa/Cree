"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/axios"

interface CreatorProfileFormProps {
  userId: number
  onSuccess?: () => void
}

export default function CreatorProfileForm({ userId, onSuccess }: CreatorProfileFormProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  const [formData, setFormData] = useState({
    full_name: "",
    location: "",
    category: "",
    primary_platform: "Instagram",
    instagram_username: "",
    instagram_profile_link: "",
    youtube_username: "",
    youtube_profile_link: "",
    bio: "",
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")
    setSuccess("")

    try {
      await api.put(`/users/creator-profile/${userId}`, formData)

      // Auto-trigger Instagram scraping if username provided
      if (formData.instagram_username) {
        try {
          await api.post(`/instagram/scrape/${userId}`)
          setSuccess("Creator profile saved! Instagram scraping started in the background.")
        } catch (scrapeErr) {
          console.error("Auto-scrape failed:", scrapeErr)
          setSuccess("Creator profile saved! (Instagram scraping could not start automatically)")
        }
      } else {
        setSuccess("Creator profile saved successfully!")
      }

      if (onSuccess) {
        onSuccess()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {success && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-800">
          {success}
        </div>
      )}

      {/* Basic Info */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Basic Information</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="full_name">Full Name *</Label>
            <Input
              id="full_name"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              required
              placeholder="Your full name"
            />
          </div>

          <div>
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              name="location"
              value={formData.location}
              onChange={handleChange}
              placeholder="City, Country"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="category">Category *</Label>
            <Input
              id="category"
              name="category"
              value={formData.category}
              onChange={handleChange}
              required
              placeholder="e.g., Fashion, Tech, Gaming"
            />
          </div>

          <div>
            <Label htmlFor="primary_platform">Primary Platform *</Label>
            <select
              id="primary_platform"
              name="primary_platform"
              value={formData.primary_platform}
              onChange={handleChange}
              className="w-full px-3 py-2 border rounded-md"
              required
            >
              <option value="Instagram">Instagram</option>
              <option value="YouTube">YouTube</option>
            </select>
          </div>
        </div>

        <div>
          <Label htmlFor="bio">Bio</Label>
          <Textarea
            id="bio"
            name="bio"
            value={formData.bio}
            onChange={handleChange}
            placeholder="Tell us about yourself"
            rows={3}
          />
        </div>
      </div>

      {/* Instagram */}
      <div className="space-y-4 p-4 border rounded-lg bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">📸</span> Instagram
        </h3>

        <div>
          <Label htmlFor="instagram_username">Instagram Username</Label>
          <Input
            id="instagram_username"
            name="instagram_username"
            value={formData.instagram_username}
            onChange={handleChange}
            placeholder="@username (without @)"
          />
           <p className="text-sm text-muted-foreground">
            Enter your Instagram handle (without @)
            </p>
        </div>

        <div>
          <Label htmlFor="instagram_profile_link">Instagram Profile Link</Label>
          <Input
            id="instagram_profile_link"
            name="instagram_profile_link"
            value={formData.instagram_profile_link}
            onChange={handleChange}
            placeholder="https://instagram.com/username"
          />
        </div>
      </div>

      {/* YouTube */}
      <div className="space-y-4 p-4 border rounded-lg bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">▶️</span> YouTube
        </h3>

        <div>
          <Label htmlFor="youtube_username">YouTube Channel Name</Label>
          <Input
            id="youtube_username"
            name="youtube_username"
            value={formData.youtube_username}
            onChange={handleChange}
            placeholder="Your channel name"
          />
            <p className="text-sm text-muted-foreground">
            Enter your YouTube channel name or handle
            </p>
        </div>

        <div>
          <Label htmlFor="youtube_profile_link">YouTube Channel Link</Label>
          <Input
            id="youtube_profile_link"
            name="youtube_profile_link"
            value={formData.youtube_profile_link}
            onChange={handleChange}
            placeholder="https://youtube.com/@channelname"
          />
        </div>
      </div>

      <Button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
      >
        {loading ? "Saving..." : "Save Creator Profile"}
      </Button>
    </form>
  )
}
