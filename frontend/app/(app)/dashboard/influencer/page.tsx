"use client"
import { Sparkles } from "lucide-react"
import { AICard } from "@/components/dashboard/ai-studio-layout"
import { useHasCreatorProfile } from "@/lib/profile-status"

export default function InfluencerStudio() {
  // Gate the AI tools until a profile exists — they cannot work without one.
  const { hasProfile, loading } = useHasCreatorProfile()
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
          Creator Studio
        </h1>
        <p className="mt-4 text-lg text-gray-400">
          Everything creators need to grow with AI.
        </p>

        {locked && (
          <div className="mt-8 flex max-w-xl items-start gap-3 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.07] px-5 py-4 text-left">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" aria-hidden="true" />
            <p className="text-sm text-cyan-100/90">
              <span className="font-medium">One step to go.</span> Add your creator
              profile and social handles — we&apos;ll pull in your analytics and unlock
              your AI tools.
            </p>
          </div>
        )}

        <div className="mt-16 grid max-w-6xl gap-10 md:grid-cols-3">
          <AICard
            title="Brand Deals"
            description="Discover and apply to curated brand collaborations designed for your audience."
            action="View Deals"
            accent="indigo"
            href="/dashboard/influencer/deals"
            locked={locked}
            lockedReason="Add your profile so we can match you to brands"
            lockedHref="/dashboard/profile"
            lockedAction="Complete your profile"
          />

          <AICard
            title="AI Growth Analyzer"
            description="Understand what works, what doesn't, and how to grow faster with AI insights."
            action="Analyze Profile"
            accent="cyan"
            href="/dashboard/influencer/growth-analyzer"
            locked={locked}
            lockedReason="Link your Instagram or YouTube to analyse your growth"
            lockedHref="/dashboard/profile"
            lockedAction="Complete your profile"
          />

          <AICard
            title="Creator Support"
            description="Soon, creators will be able to collaborate with Crewaa's professional team for end-to-end
            content creation and execution."
            badge="Coming Soon"
            accent="amber"
          />
        </div>
      </main>
    </div>
  )
}
