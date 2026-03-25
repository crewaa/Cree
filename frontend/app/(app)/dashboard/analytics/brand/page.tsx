"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getCurrentUser, getSavedCreators } from "../../../../../lib/user";
import { api } from "@/lib/axios";

// Helper for parsing reasoning gracefully
const getReasoningText = (reasoning: string | null) => {
  if (!reasoning) return "Discovered via AI matching.";
  if (reasoning.startsWith('[')) {
    try {
      const parsed = JSON.parse(reasoning);
      return Array.isArray(parsed) && parsed.length > 0 ? parsed[0] : reasoning;
    } catch {
      return reasoning;
    }
  }
  return reasoning;
}

const fitColors: Record<string, string> = {
  High: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  Medium: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  Low: "bg-red-500/20 text-red-300 border-red-500/30",
}

export default function Analytics() {
  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [creators, setCreators] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function loadDashboard() {
      try {
        const userData = await getCurrentUser();
        setUser(userData);

        if (userData.role !== "BRAND") {
          router.replace("/login");
          return;
        }

        // Parallel fetch for profile and saved creators for fast loading
        const [profileRes, creatorsData] = await Promise.allSettled([
          api.get("/users/brand-profile"),
          getSavedCreators()
        ]);

        if (profileRes.status === "fulfilled") {
          setProfile(profileRes.value.data);
        }
        if (creatorsData.status === "fulfilled") {
          setCreators(creatorsData.value);
        }

      } catch (err) {
        console.error("Failed to load dashboard data", err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, [router]);

  if (loading || !user) {
    return (
      <div className="flex justify-center py-20">
         <div className="w-8 h-8 border-2 border-indigo-500/30 rounded-full animate-spin border-t-indigo-500" />
      </div>
    );
  }

  return (
    <div className="space-y-10 w-full max-w-7xl mx-auto pb-20">
      
      {/* Brand Profile Snapshot */}
      <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-8 md:p-10">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold text-white tracking-tight">
              {profile?.brand_name || "Your Brand Dashboard"}
            </h1>
            {profile ? (
               <p className="text-gray-400 text-lg">
                 {profile.industry} • {profile.campaign_goal} Campaign Focus
               </p>
            ) : (
               <p className="text-gray-400 text-lg">
                 Complete your Brand Profile to get personalized AI matching.
               </p>
            )}
          </div>
          <Link href="/dashboard/brand-profile">
            <button className="px-6 py-2.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/5 text-white text-sm font-medium transition cursor-pointer">
              {profile ? "Edit Profile" : "Setup Profile"}
            </button>
          </Link>
        </div>

        {profile && (
          <div className="relative z-10 grid grid-cols-2 md:grid-cols-4 gap-6 mt-10 p-6 rounded-2xl bg-black/40 border border-white/5">
            <div>
               <p className="text-sm text-gray-500 mb-1">Target Location</p>
               <p className="font-medium text-gray-200">{profile.target_location || "Global"}</p>
            </div>
            <div>
               <p className="text-sm text-gray-500 mb-1">Budget</p>
               <p className="font-medium text-gray-200">{profile.budget_range}</p>
            </div>
            <div>
               <p className="text-sm text-gray-500 mb-1">Platforms</p>
               <p className="font-medium text-gray-200 capitalize">
                 {(() => {
                    try {
                      return JSON.parse(profile.platform_preferences || "[]").join(", ") || "All"
                    } catch { return "All" }
                 })()}
               </p>
            </div>
            <div>
               <p className="text-sm text-gray-500 mb-1">Website</p>
               {profile.website ? (
                  <a href={profile.website} target="_blank" rel="noreferrer" className="font-medium text-indigo-400 hover:underline inline-block truncate max-w-[150px]">
                    {profile.website.replace(/^https?:\/\//, '')}
                  </a>
               ) : (
                  <p className="font-medium text-gray-500">Not set</p>
               )}
            </div>
          </div>
        )}
      </section>

      {/* Discovered Creators Section */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white/90">
              Recently Discovered Creators
            </h2>
            <p className="text-gray-400 text-sm mt-1">Found using AI Campaign Matching</p>
          </div>
          <div className="text-sm font-medium text-indigo-400 bg-indigo-500/10 px-4 py-1.5 rounded-full">
            {creators.length} saved
          </div>
        </div>

        {creators.length === 0 ? (
          <div className="rounded-2xl border border-white/5 bg-[#0E1220]/50 p-12 text-center">
            <p className="text-4xl mb-4">✨</p>
            <h3 className="text-lg font-medium text-white mb-2">No creators discovered yet</h3>
            <p className="text-gray-400 max-w-md mx-auto mb-6">
              Use the Discover Creators tool in Brand Studio to let AI find the perfect matches for your upcoming campaigns.
            </p>
            <Link href="/dashboard/brand/discover">
               <button className="px-6 py-3 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition cursor-pointer shadow-lg shadow-indigo-500/20">
                 Find Creators Now
               </button>
            </Link>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {creators.map((creator) => (
              <div 
                key={creator.id}
                className="group relative overflow-hidden flex flex-col justify-between rounded-2xl border border-white/10 bg-[#0E1220]/50 p-6 transition-all hover:border-indigo-500/50 hover:bg-[#0E1220]"
              >
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-white">{creator.creator_name || "Unknown Creator"}</h3>
                      <p className="text-sm text-indigo-400">{creator.creator_category || "General"} • {creator.creator_platform || "Instagram"}</p>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-medium uppercase tracking-wider border ${fitColors[creator.fit_level] || fitColors["Low"]}`}>
                      {creator.fit_level} FIT
                    </span>
                  </div>

                  <div className="relative mb-6">
                     <p className="text-sm text-gray-400 line-clamp-4 leading-relaxed relative z-10">
                       {getReasoningText(creator.score_reasoning)}
                     </p>
                     <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-[#0E1220] group-hover:from-transparent to-transparent z-20 transition" />
                  </div>
                </div>
                
                <div className="pt-4 border-t border-white/10 flex justify-between items-center mt-auto">
                   <span className="text-xs text-gray-500">
                     Matched on {new Date(creator.saved_at).toLocaleDateString()}
                   </span>
                   <Link href={`/dashboard/brand/creators/${creator.creator_id}`} className="text-xs font-semibold text-white group-hover:text-indigo-400 transition">
                     View Complete Profile →
                   </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}