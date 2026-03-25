"use client"
import { AICard } from "../../../../components/dashboard/ai-studio-layout"

export default function InfluencerStudio() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#06070C] text-white">

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

        <div className="mt-16 grid max-w-6xl gap-10 md:grid-cols-3">
          <AICard
            title="Brand Deals"
            description="Discover and apply to curated brand collaborations designed for your audience."
            action="View Deals"
            accent="indigo"
            href="/dashboard/influencer/deals"
          />

          <AICard
            title="AI Growth Analyzer"
            description="Understand what works, what doesn't, and how to grow faster with AI insights."
            action="Analyze Profile"
            accent="cyan"
            href="/dashboard/influencer/growth-analyzer"
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
