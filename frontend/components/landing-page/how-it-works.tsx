import { FadeIn } from "../motion/fade-in"

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
      <section className="mx-auto max-w-7xl px-6 py-24">
        <h2 className="text-3xl font-semibold text-center text-white">
          How it works
        </h2>
  
        <div className="mt-16 grid gap-12 md:grid-cols-3">
          {steps.map((item, index) => (
            <FadeIn key={item.step} delay={index * 0.05}>
            <div key={item.step} className="text-center">
              <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full border border-white/10 text-indigo-400 font-medium">
                {item.step}
              </div>
              <h3 className="mt-6 text-lg font-medium text-white">
                {item.title}
              </h3>
              <p className="mt-2 text-sm text-gray-400">
                {item.description}
              </p>
            </div>
            </FadeIn>
          ))}
        </div>
      </section>
    )
  }
  