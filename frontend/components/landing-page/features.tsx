import { Card } from "@/components/ui/card"
import { FadeIn } from "../motion/fade-in"
import ShimmerField from "./shimmer-field"

const features = [
  {
    title: "Smart Influencer Discovery",
    description:
      "Find creators based on niche, engagement, audience demographics, and performance.",
  },
  {
    title: "Campaign Management",
    description:
      "Create campaigns, invite influencers, track progress, and manage deliverables.",
  },
  {
    title: "Secure Payments",
    description:
      "Handle contracts and payments securely with built-in escrow and payouts.",
  },
  {
    title: "Real-Time Collaboration",
    description:
      "Chat, negotiate, and collaborate directly inside the platform.",
  },
  {
    title: "Performance Analytics",
    description:
      "Track campaign reach, engagement, and ROI with actionable insights.",
  },
  {
    title: "AI-Powered Matching",
    description:
      "Get smart recommendations for creators and pricing using AI.",
  },
]

export function LandingPageFeaturesSection() {
  return (
    <section className="px-6 py-24">
      <ShimmerField className="mx-auto max-w-7xl px-8 py-14 sm:px-10">
        <h2 className="text-center text-3xl font-semibold text-white">
          Everything you need to collaborate at scale
        </h2>

        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => (
            <FadeIn key={feature.title} delay={index * 0.05}>
              <Card
                className="bg-white/[0.035] border border-white/8 p-6 backdrop-blur-xs transition hover:border-cyan-200/15 hover:bg-white/[0.05]"
              >
                <h3 className="text-lg font-medium text-white">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-300">
                  {feature.description}
                </p>
              </Card>
            </FadeIn>
          ))}
        </div>
      </ShimmerField>
    </section>
  )
}
