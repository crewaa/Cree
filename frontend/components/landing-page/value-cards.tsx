import ShimmerField from "./shimmer-field";

const values = [
  {
    title: "Curated Discovery",
    description:
      "Brands discover creators based on relevance, not randomness.",
  },
  {
    title: "Direct Collaboration",
    description:
      "Creators work directly with brands without agency barriers.",
  },
  {
    title: "Smart Insights",
    description:
      "Creators get visibility into how their profile performs.",
  },
];

export default function ValueCards() {
  return (
    <section className="px-6 pb-24">
      <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-3">
        {values.map((item, index) => (
          <ShimmerField
            key={item.title}
            tone={index % 2 === 0 ? "indigo" : "cyan"}
            className="group rounded-[1.5rem] transition-transform duration-300 hover:-translate-y-1"
          >
            <div className="relative overflow-hidden px-6 py-8 text-center">
              <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent" />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.12),transparent_38%)] opacity-70" />
              <div className="relative z-10">
                <h3 className="text-lg font-semibold text-white">
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-slate-300">
                  {item.description}
                </p>
              </div>
            </div>
          </ShimmerField>
        ))}
      </div>
    </section>
  );
}
