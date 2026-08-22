"use client"
import { Sparkles } from "lucide-react"
import { AICard } from "@/components/dashboard/ai-studio-layout"
import { useHasBrandProfile } from "@/lib/profile-status"

export default function BrandStudio() {
  const { hasProfile, loading } = useHasBrandProfile()
  const locked = !loading && hasProfile === false

  return (
    <div className="relative relative overflow-hidden">

      {/* Background Effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full 
                        bg-indigo-500/20 blur-[140px] animate-[floatSlow_18s_ease-in-out_infinite]" />
        <div className="absolute bottom-[-30%] left-[10%] h-[500px] w-[500px] rounded-full 
                        bg-cyan-500/15 blur-[140px]" />
        <div className="absolute bottom-[-30%] right-[10%] h-[500px] w-[500px] rounded-full 
                        bg-amber-500/15 blur-[160px]" />
      </div>

      {/* Content */}
      <main className="relative z-10 flex min-h-screen flex-col items-center justify-center px-6">
        <h1 className="text-5xl md:text-6xl font-semibold tracking-tight">
          Brand Studio
        </h1>
        <p className="mt-4 text-lg text-gray-400">
          Smarter collaborations powered by AI.
        </p>

        {locked && (
          <div className="mt-8 flex max-w-xl items-start gap-3 rounded-xl border border-indigo-400/20 bg-indigo-400/[0.07] px-5 py-4 text-left">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-indigo-300" aria-hidden="true" />
            <p className="text-sm text-indigo-100/90">
              <span className="font-medium">One step to go.</span> Add your brand
              profile — industry, budget and goals — so we can match you to the right
              creators.
            </p>
          </div>
        )}

        <div className="mt-16 grid max-w-6xl gap-10 md:grid-cols-3">
          <AICard
            title="Discover Creators"
            description="Find verified creators perfectly matched to your brand and campaign goals."
            action="Discover"
            accent="indigo"
            href="/dashboard/brand/discover"
            locked={locked}
            lockedReason="Tell us about your brand so we can match creators"
            lockedHref="/dashboard/brand-profile"
            lockedAction="Complete brand profile"
          />

          <AICard
            title="Interested Creators"
            description="Creators who responded to your opportunities, with their contact details."
            action="View Responses"
            accent="cyan"
            href="/dashboard/brand/interested"
            locked={locked}
            lockedReason="Complete your brand profile to start receiving responses"
            lockedHref="/dashboard/brand-profile"
            lockedAction="Complete brand profile"
          />

          <AICard
            title="Campaigns"
            description="State your real fee, deliverables and deadline. Creators see exactly what you offer."
            action="Manage Campaigns"
            accent="amber"
            href="/dashboard/brand/campaigns"
            locked={locked}
            lockedReason="Complete your brand profile to create campaigns"
            lockedHref="/dashboard/brand-profile"
            lockedAction="Complete brand profile"
          />

          <AICard
            title="AI Influencer"
            description="Create AI-powered virtual influencers tailored to your brand, ready to front campaigns without relying on a human creator."
            badge="Coming Soon"
            accent="indigo"
          />

          <AICard
            title="AI Marketing Suite"
            description="Run intelligent, data-driven marketing campaigns with AI — from content strategy to performance optimization."
            badge="Coming Soon"
            accent="cyan"
          />
        </div>
      </main>
    </div>
  )
}
