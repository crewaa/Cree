"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { getAdminUserDetail, deleteAdminUser, AdminUserDetail } from "@/lib/admin"
import {
  ArrowLeft, Trash2, Loader2, Mail, ShieldCheck,
  MapPin, Tag, Instagram, Youtube, Globe, Target, DollarSign,
  Building2, UserRound, Calendar,
} from "lucide-react"
import { useToast } from "@/components/ui/toast"
import { errorMessage } from "@/lib/types"

export default function AdminUserDetailPage() {
  const router = useRouter()
  const toast = useToast()
  const params = useParams()
  const userId = Number(params.id)

  const [user, setUser] = useState<AdminUserDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const data = await getAdminUserDetail(userId)
        setUser(data)
      } catch (err) {
        console.error("Failed to load user:", err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [userId])

  async function handleDelete() {
    setDeleting(true)
    try {
      await deleteAdminUser(userId)
      router.push("/dashboard/admin/users")
    } catch (err) {
      // Previously console-only: the modal simply stopped with no explanation.
      toast.error(errorMessage(err, "Could not delete this user. Please try again."))
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center  gap-4">
        <p className="text-gray-400">User not found</p>
        <button
          onClick={() => router.push("/dashboard/admin/users")}
          className="text-indigo-400 hover:underline cursor-pointer"
        >
          ← Back to users
        </button>
      </div>
    )
  }

  const roleLabel = user.role === "INFLUENCER" ? "Creator" : user.role === "BRAND" ? "Brand" : "Admin"
  const roleColor =
    user.role === "INFLUENCER"
      ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
      : user.role === "BRAND"
        ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
        : "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"

  return (
    <div className="relative relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/8 blur-[160px]" />
      </div>

      <div className="relative z-10 mx-auto max-w-4xl px-6 py-10">
        {/* Back + Actions */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => router.push("/dashboard/admin/users")}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition cursor-pointer"
          >
            <ArrowLeft className="h-4 w-4" /> Back to users
          </button>

          {user.role !== "ADMIN" && (
            <button
              onClick={() => setShowDelete(true)}
              className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-400 hover:bg-red-500/20 transition cursor-pointer"
            >
              <Trash2 className="h-4 w-4" /> Delete User
            </button>
          )}
        </div>

        {/* User Header Card */}
        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black mb-8">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-transparent" />
          <div className="relative z-10 p-8">
            <div className="flex flex-col md:flex-row md:items-center gap-6">
              {/* Avatar */}
              <div className="h-20 w-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-3xl font-bold shrink-0">
                {user.email.charAt(0).toUpperCase()}
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <h1 className="text-2xl font-semibold">
                    {user.role === "INFLUENCER" && user.creator_full_name
                      ? user.creator_full_name
                      : user.role === "BRAND" && user.brand_name
                        ? user.brand_name
                        : user.email.split("@")[0]}
                  </h1>
                  <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${roleColor}`}>
                    {roleLabel}
                  </span>
                  {user.is_active ? (
                    <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" /> Active
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5 text-xs text-gray-500">
                      <span className="h-2 w-2 rounded-full bg-gray-500" /> Inactive
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <Mail className="h-4 w-4" />
                  {user.email}
                </div>
                <div className="flex items-center gap-2 text-gray-500 text-sm mt-1">
                  <ShieldCheck className="h-4 w-4" />
                  User ID: #{user.id}
                </div>
                <div className="flex items-center gap-2 text-gray-500 text-sm mt-1">
                  <Calendar className="h-4 w-4" />
                  Joined {new Date(user.created_at).toLocaleDateString(undefined, {
                    year: "numeric", month: "long", day: "numeric",
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Creator Profile Details */}
        {user.role === "INFLUENCER" && (
          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black overflow-hidden">
            <div className="border-b border-white/10 px-8 py-5">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <UserRound className="h-4 w-4 text-cyan-400" /> Creator Profile
                {user.creator_profile_completed ? (
                  <span className="ml-2 rounded-full bg-emerald-500/20 px-3 py-0.5 text-xs text-emerald-400">
                    Completed
                  </span>
                ) : (
                  <span className="ml-2 rounded-full bg-amber-500/20 px-3 py-0.5 text-xs text-amber-400">
                    Incomplete
                  </span>
                )}
              </h2>
              {/* The badge alone used to be the whole story, and it always said
                  "Completed". Naming what is missing is what makes it useful. */}
              {!user.creator_profile_completed && !!user.creator_profile_missing?.length && (
                <p className="mt-2 text-sm text-amber-300/80">
                  Missing: {user.creator_profile_missing.join(", ")}
                </p>
              )}
            </div>

            {user.creator_full_name ? (
              <div className="p-8 grid gap-6 md:grid-cols-2">
                <InfoItem icon={<Tag className="h-4 w-4" />} label="Category" value={user.creator_category} />
                <InfoItem icon={<MapPin className="h-4 w-4" />} label="Location" value={user.creator_location} />
                <InfoItem icon={<Globe className="h-4 w-4" />} label="Primary Platform" value={user.creator_primary_platform} />
                <InfoItem icon={<Instagram className="h-4 w-4" />} label="Instagram" value={user.creator_instagram_username ? `@${user.creator_instagram_username}` : undefined} />
                <InfoItem icon={<Youtube className="h-4 w-4" />} label="YouTube" value={user.creator_youtube_username ? `@${user.creator_youtube_username}` : undefined} />
                {user.creator_bio && (
                  <div className="md:col-span-2">
                    <p className="text-xs text-gray-500 mb-1">Bio</p>
                    <p className="text-sm text-gray-300 leading-relaxed">{user.creator_bio}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center text-gray-500">
                No creator profile has been set up yet.
              </div>
            )}
          </div>
        )}

        {/* Brand Profile Details */}
        {user.role === "BRAND" && (
          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black overflow-hidden">
            <div className="border-b border-white/10 px-8 py-5">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Building2 className="h-4 w-4 text-amber-400" /> Brand Profile
                {user.brand_profile_completed ? (
                  <span className="ml-2 rounded-full bg-emerald-500/20 px-3 py-0.5 text-xs text-emerald-400">
                    Completed
                  </span>
                ) : (
                  <span className="ml-2 rounded-full bg-amber-500/20 px-3 py-0.5 text-xs text-amber-400">
                    Incomplete
                  </span>
                )}
              </h2>
              {!user.brand_profile_completed && !!user.brand_profile_missing?.length && (
                <p className="mt-2 text-sm text-amber-300/80">
                  Missing: {user.brand_profile_missing.join(", ")}
                </p>
              )}
            </div>

            {user.brand_name ? (
              <div className="p-8 grid gap-6 md:grid-cols-2">
                <InfoItem icon={<Tag className="h-4 w-4" />} label="Industry" value={user.brand_industry} />
                <InfoItem icon={<Globe className="h-4 w-4" />} label="Website" value={user.brand_website} />
                <InfoItem icon={<Target className="h-4 w-4" />} label="Campaign Goal" value={user.brand_campaign_goal} />
                <InfoItem icon={<DollarSign className="h-4 w-4" />} label="Budget Range" value={user.brand_budget_range} />
                {user.brand_description && (
                  <div className="md:col-span-2">
                    <p className="text-xs text-gray-500 mb-1">Description</p>
                    <p className="text-sm text-gray-300 leading-relaxed">{user.brand_description}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center text-gray-500">
                No brand profile has been set up yet.
              </div>
            )}
          </div>
        )}

        {/* Admin user — no profile */}
        {user.role === "ADMIN" && (
          <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black p-8 text-center">
            <ShieldCheck className="h-12 w-12 text-emerald-400 mx-auto mb-4" />
            <h2 className="text-lg font-semibold mb-2">Admin Account</h2>
            <p className="text-gray-400">
              Admin accounts do not have creator or brand profiles.
            </p>
          </div>
        )}
      </div>

      {/* Delete Modal */}
      {showDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0E1220] p-8">
            <h2 className="text-xl font-semibold mb-2">Delete User</h2>
            <p className="text-gray-400 mb-4">
              This will permanently delete <span className="text-white font-medium">{user.email}</span> and all associated data.
            </p>
            <p className="text-xs text-red-400/80 mb-6">
              All profiles, Instagram data, YouTube data, and saved creators will be permanently destroyed.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDelete(false)}
                className="rounded-xl border border-white/10 px-5 py-2.5 text-sm font-medium hover:bg-white/10 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2.5 text-sm font-medium hover:bg-red-500 transition disabled:opacity-50 cursor-pointer"
              >
                {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
                Delete User
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function InfoItem({ icon, label, value }: { icon: React.ReactNode; label: string; value?: string | null }) {
  return (
    <div>
      <p className="flex items-center gap-1.5 text-xs text-gray-500 mb-1">
        {icon} {label}
      </p>
      <p className="text-sm font-medium text-gray-200">
        {value || <span className="text-gray-600">Not provided</span>}
      </p>
    </div>
  )
}
