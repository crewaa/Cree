/**
 * Placeholder shown while the session loads.
 *
 * Replaces the previous `return null`, which produced a blank white flash on
 * every navigation. Matching the shell's dark surface means the transition
 * reads as loading rather than as a broken page.
 */
export function AppShellSkeleton() {
  return (
    <div className="min-h-screen bg-[#06070C]" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading your dashboard…</span>

      {/* Navbar placeholder */}
      <div className="flex h-16 items-center justify-between border-b border-white/5 px-6">
        <div className="h-5 w-24 animate-pulse rounded bg-white/10" />
        <div className="flex items-center gap-4">
          <div className="h-5 w-20 animate-pulse rounded bg-white/10" />
          <div className="h-9 w-9 animate-pulse rounded-full bg-white/10" />
        </div>
      </div>

      {/* Content placeholder */}
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="h-10 w-64 animate-pulse rounded-lg bg-white/10" />
        <div className="mt-4 h-4 w-96 max-w-full animate-pulse rounded bg-white/5" />

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-56 animate-pulse rounded-2xl border border-white/5 bg-white/[0.03]"
            />
          ))}
        </div>
      </div>
    </div>
  )
}
