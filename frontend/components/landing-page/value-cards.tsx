const values = [
    {
      title: "Curated Discovery",
      description:
        "Brands discover creators based on relevance, not randomness.",
    },
    {
      title: "Direct Collaboration",
      description:
        "Creators work directly with brands — no agency barriers.",
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
          {values.map((item) => (
            <div
            key={item.title}
            className="
              group relative overflow-hidden rounded-xl
              bg-white p-6 text-center
              border border-slate-200
              transition-all duration-300
              hover:-translate-y-1 hover:shadow-2xl
            "
          >
            {/* Animated Gradient */}
            <div className="
            absolute inset-0
            bg-[linear-gradient(120deg,transparent,rgba(99,102,241,0.25),rgba(34,211,238,0.25),transparent)]
            animate-[shine_6s_linear_infinite]
            " />

            {/* <div
              className="
                pointer-events-none absolute inset-0
                bg-[linear-gradient(120deg,transparent,rgba(99,102,241,0.35),rgba(34,211,238,0.35),transparent)]
                -translate-x-full
                group-hover:animate-[shine_1.8s_linear_infinite]
              "
            /> */}
          
            <h3 className="relative z-10 text-lg font-semibold text-slate-900">
              {item.title}
            </h3>
          
            <p className="relative z-10 mt-2 text-sm text-slate-600">
              {item.description}
            </p>
          </div>           
          ))}
        </div>
      </section>
    );
  }
  