import Link from "next/link"
import { FadeIn } from "../motion/fade-in"
import GradientBackground from "./gradient-background"
import ShimmerField from "./shimmer-field"
import { FlipWords } from "../ui/flip-words"

export function LandingPageHeroSection() {
  const words = ["Brand", "Creator"]
  const subwords = ["Creators", "Brands"]
  const trustPoints = [
    "Verified profiles",
    "Direct collaboration",
    "Performance insights",
  ]

  return (
    <GradientBackground>
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute -top-24 left-1/2 h-[28rem] w-[40rem] -translate-x-1/2 rounded-full bg-indigo-500/12 blur-[120px]" />
          <div className="absolute right-1/4 top-36 h-[22rem] w-[28rem] rounded-full bg-cyan-400/8 blur-[120px]" />
          <div className="absolute left-1/4 top-48 h-[18rem] w-[22rem] rounded-full bg-cyan-300/5 blur-[110px]" />
        </div>

        <div className="mx-auto max-w-7xl px-6 pb-28 pt-36 text-center sm:pt-40">
          <ShimmerField className="mx-auto max-w-5xl px-8 py-12 sm:px-12 sm:py-14">
            <FadeIn>
              <div className="mx-auto inline-flex rounded-full border border-cyan-200/12 bg-white/[0.04] px-4 py-1 text-xs font-medium uppercase tracking-[0.28em] text-cyan-100/75">
                Creator x Brand Collaboration
              </div>
            </FadeIn>

            <FadeIn>
              <h1 className="mt-6 text-5xl font-bold tracking-tight text-white md:text-6xl">
                Crewaa where brands and creators
                <br />
                <span className="bg-linear-to-r from-indigo-200 via-cyan-200 to-cyan-300 bg-clip-text text-transparent">
                  collaborate with intelligence
                </span>
              </h1>
            </FadeIn>

            <FadeIn delay={0.1}>
              <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-300">
                Crewaa is a curated collaboration platform that connects brands
                with verified creators without agencies, without noise, and with
                complete transparency.
              </p>
            </FadeIn>

            <FadeIn delay={0.2}>
              <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
                <Link href="/signup/brand">
                  <button className="rounded-xl border border-cyan-200/10 bg-white/[0.08] px-6 py-3 font-medium text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] transition hover:bg-cyan-300/14">
                    Join as Brand
                  </button>
                </Link>

                <Link href="/signup/influencer">
                  <button className="rounded-xl border border-white/10 px-6 py-3 font-medium text-slate-200 transition hover:border-cyan-200/16 hover:bg-white/[0.04] hover:text-white">
                    Join as Creator
                  </button>
                </Link>
              </div>
            </FadeIn>

            <FadeIn delay={0.3}>
              <div className="mx-auto mt-10 text-3xl font-normal text-white sm:text-4xl">
                Join as
                <FlipWords words={words} /> <br />
                and collaborate with
                <FlipWords words={subwords} />
              </div>
            </FadeIn>

            <FadeIn delay={0.4}>
              <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
                {trustPoints.map((point) => (
                  <span
                    key={point}
                    className="rounded-full border border-white/8 bg-white/[0.035] px-4 py-2 text-sm text-slate-300"
                  >
                    {point}
                  </span>
                ))}
              </div>
            </FadeIn>
          </ShimmerField>
        </div>
      </section>
    </GradientBackground>
  )
}
