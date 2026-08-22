"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getAdminStats, PlatformStats } from "@/lib/admin"
import { Users, Palette, Building2, ShieldCheck, ArrowRight, UserPlus } from "lucide-react"

export default function AdminDashboard() {
  const router = useRouter()
  const [stats, setStats] = useState<PlatformStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const data = await getAdminStats()
        setStats(data)
      } catch (err) {
        console.error("Failed to load admin stats:", err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const statCards = stats
    ? [
        {
          label: "Total Users",
          value: stats.total_users,
          icon: Users,
          gradient: "from-indigo-500 to-indigo-700",
          glow: "bg-indigo-500/20",
        },
        {
          label: "Creators",
          value: stats.total_creators,
          icon: Palette,
          gradient: "from-cyan-500 to-cyan-700",
          glow: "bg-cyan-500/20",
        },
        {
          label: "Brands",
          value: stats.total_brands,
          icon: Building2,
          gradient: "from-amber-500 to-amber-700",
          glow: "bg-amber-500/20",
        },
        {
          label: "Admins",
          value: stats.total_admins,
          icon: ShieldCheck,
          gradient: "from-emerald-500 to-emerald-700",
          glow: "bg-emerald-500/20",
        },
        {
          label: "New (Last 7 Days)",
          value: stats.new_users_last_7_days,
          icon: UserPlus,
          gradient: "from-fuchsia-500 to-fuchsia-700",
          glow: "bg-fuchsia-500/20",
        },
      ]
    : []

  return (
    <div className="relative relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/10 blur-[160px]" />
        <div className="absolute bottom-[-30%] left-[10%] h-[500px] w-[500px] rounded-full bg-cyan-500/10 blur-[160px]" />
        <div className="absolute bottom-[-20%] right-[10%] h-[500px] w-[500px] rounded-full bg-amber-500/10 blur-[160px]" />
      </div>

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-7xl px-6 py-12">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck className="h-8 w-8 text-indigo-400" />
            <h1 className="text-4xl md:text-5xl font-semibold tracking-tight">
              Admin Console
            </h1>
          </div>
          <p className="text-lg text-gray-400 mt-2">
            Full platform oversight — manage creators, brands, and everything in between.
          </p>
        </div>

        {/* Stats Grid */}
        {loading ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-5">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="h-[140px] rounded-2xl border border-white/10 bg-white/5 animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-5">
            {statCards.map((card) => (
              <div
                key={card.label}
                className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl group"
              >
                {/* Accent glow */}
                <div className={`absolute top-0 right-0 h-32 w-32 rounded-full ${card.glow} blur-[60px] opacity-60`} />

                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-gray-400">
                      {card.label}
                    </span>
                    <div className={`rounded-xl bg-gradient-to-br ${card.gradient} p-2`}>
                      <card.icon className="h-5 w-5 text-white" />
                    </div>
                  </div>
                  <p className="text-4xl font-bold tracking-tight">
                    {card.value}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Quick Actions */}
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <button
            onClick={() => router.push("/dashboard/admin/users")}
            className="group relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black px-8 py-10 text-left transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl cursor-pointer"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/20 via-indigo-400/10 to-transparent" />
            <div className="relative z-10">
              <Users className="h-8 w-8 text-indigo-400 mb-4" />
              <h3 className="text-2xl font-semibold mb-2">User Management</h3>
              <p className="text-gray-400 mb-6">
                View, search, and manage all creators and brands on the platform.
              </p>
              <div className="flex items-center gap-2 text-sm font-medium text-indigo-400 group-hover:gap-3 transition-all">
                Manage Users <ArrowRight className="h-4 w-4" />
              </div>
            </div>
          </button>

          <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black px-8 py-10 text-left">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 via-cyan-400/10 to-transparent" />
            <div className="relative z-10">
              <Palette className="h-8 w-8 text-cyan-400 mb-4" />
              <h3 className="text-2xl font-semibold mb-2">Creator Analytics</h3>
              <p className="text-gray-400 mb-6">
                Deep-dive into creator performance, engagement metrics, and growth.
              </p>
              <span className="rounded-full bg-white/10 px-4 py-1 text-sm text-gray-300">
                Coming Soon
              </span>
            </div>
          </div>

          <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black px-8 py-10 text-left">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-500/20 via-amber-400/10 to-transparent" />
            <div className="relative z-10">
              <Building2 className="h-8 w-8 text-amber-400 mb-4" />
              <h3 className="text-2xl font-semibold mb-2">Brand Campaigns</h3>
              <p className="text-gray-400 mb-6">
                Monitor brand campaigns, budgets, and creator collaborations.
              </p>
              <span className="rounded-full bg-white/10 px-4 py-1 text-sm text-gray-300">
                Coming Soon
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
