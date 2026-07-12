import { FadeIn } from "../motion/fade-in"
import ShimmerField from "./shimmer-field"

const steps = [
    {
      step: "01",
      title: "Join Crewaa",
      description:
        "Brands and creators register and create verified profiles.",
    },
    {
      step: "02",
      title: "Discover & Connect",
      description:
        "Brands submit requirements. Creators explore live brand deals.",
    },
    {
      step: "03",
      title: "Collaborate",
      description:
        "Shortlisted creators collaborate directly with brands.",
    },
  ]
  
  export function HowItWorksSection() {
    return (
      <section className="px-6 py-24">
        <ShimmerField tone="cyan" className="mx-auto max-w-7xl px-8 py-16 sm:px-10">
          <h2 className="text-center text-3xl font-semibold text-white">
            How it works
          </h2>
    
          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {steps.map((item, index) => (
              <FadeIn key={item.step} delay={index * 0.05}>
                <div className="rounded-[1.5rem] border border-white/7 bg-white/[0.025] px-6 py-8 text-center backdrop-blur-[2px]">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-cyan-200/15 bg-white/[0.03] font-medium text-cyan-200">
                    {item.step}
                  </div>
                  <h3 className="mt-6 text-lg font-medium text-white">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    {item.description}
                  </p>
                </div>
              </FadeIn>
            ))}
          </div>
        </ShimmerField>
      </section>
    )
  }
  
