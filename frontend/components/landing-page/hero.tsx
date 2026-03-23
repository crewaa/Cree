import { FadeIn } from "../motion/fade-in"
import Link from "next/link"
import GradientBackground from "./gradient-background"
import { FlipWords } from "../ui/flip-words"


export function LandingPageHeroSection() {

  const words = ["Brand", "Creator"];
  const subwords = ["Creators", "Brands"];

    return (
      <GradientBackground>
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 h-125 w-200 rounded-full bg-indigo-500/20 blur-[120px]" />
          <div className="absolute top-40 right-1/3 h-100 w-150 rounded-full bg-cyan-400/10 blur-[120px]" />
        </div>

        <div className="mx-auto max-w-7xl px-6 pt-40 pb-32 text-center">
        <FadeIn>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight text-white">
            Crewaa Where Brands and Creators 
            <br />
            <span className="bg-linear-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            Collaborate with Intelligence
            </span>
          </h1>
          </FadeIn>
  
        <FadeIn delay={0.1}>
          <p className="mt-6 text-lg text-gray-400 max-w-2xl mx-auto">
            Crewaa is a curated collaboration platform that connects brands with verified creators —
            without agencies, without noise, and with complete transparency.
          </p>
          </FadeIn>
  
          <FadeIn delay={0.2}>
          <div className="mt-10 flex items-center justify-center gap-4">

            <Link href="/signup/brand">
            <button className="px-6 py-3 rounded-md bg-indigo-500 hover:bg-indigo-400 text-white font-medium transition">
              Join as Brand
            </button>
            </Link>

            <Link href="/signup/influencer">
            <button className="px-6 py-3 rounded-md border border-white/10 text-gray-300 hover:text-white hover:border-white/20 transition">
              Join as Creator
            </button>
            </Link>
          </div>
          <div className="text-4xl mt-10 mx-auto font-normal text-white dark:text-white">
            Join as
            <FlipWords words={words} /> <br></br>
            and collaborate with
            <FlipWords words={subwords} />
          </div>
          </FadeIn>
        </div>
      </section>
      </GradientBackground>
    )
  }
  