import ShimmerField from "./shimmer-field";

export default function WhatIsCrewaa() {
  return (
    <section className="px-6 py-24">
      <ShimmerField className="mx-auto max-w-5xl px-8 py-20 text-center sm:px-12">
        <div className="mx-auto max-w-3xl space-y-4">
          <div className="mx-auto inline-flex rounded-full border border-cyan-300/20 bg-white/6 px-4 py-1 text-sm tracking-[0.24em] text-cyan-100/80 uppercase">
            The Collaboration Layer
          </div>
          <h2 className="text-3xl font-semibold">What is Crewaa?</h2>
          <p className="text-lg text-slate-300">
            Crewaa is a collaboration ecosystem designed to help brands discover
            the right creators and help creators access meaningful brand
            opportunities — all in one place.
          </p>
        </div>
      </ShimmerField>
    </section>
  );
}
