import Link from "next/link"

export const metadata = { title: "Page not found · Crewaa" }

/**
 * 404. Previously a mistyped URL rendered Next's default page, which carries
 * no branding and no way back into the product.
 */
export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#06070C] px-6 text-center text-white">
      <p className="text-sm font-medium uppercase tracking-[0.28em] text-cyan-200/70">
        404
      </p>
      <h1 className="mt-4 text-4xl font-semibold tracking-tight md:text-5xl">
        We couldn&apos;t find that page
      </h1>
      <p className="mt-4 max-w-md text-gray-400">
        The link may be out of date, or the page may have moved.
      </p>
      <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/"
          className="rounded-xl bg-white px-6 py-3 font-medium text-black transition hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
        >
          Back to home
        </Link>
        <Link
          href="/login"
          className="rounded-xl border border-white/15 px-6 py-3 font-medium text-gray-200 transition hover:bg-white/5 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
        >
          Log in
        </Link>
      </div>
    </main>
  )
}
