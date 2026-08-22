"use client"

import Link from "next/link"
import { Lock } from "lucide-react"

/**
 * A studio feature card.
 *
 * `locked` exists because of a real onboarding dead end: a brand-new creator
 * landed here with no profile, clicked "Analyze Profile", waited ~7 seconds and
 * got a raw 404 telling them to complete a profile — with no link to it. A
 * locked card explains the prerequisite up front and links straight to it.
 */
export function AICard({
  title,
  description,
  action,
  badge,
  accent = "indigo",
  href,
  onClick,
  locked = false,
  lockedReason,
  lockedHref,
  lockedAction,
}: {
  title: string
  description: string
  action?: string
  badge?: string
  accent?: "indigo" | "cyan" | "amber"
  href?: string
  onClick?: () => void
  /** Disables the action and explains what to do first. */
  locked?: boolean
  lockedReason?: string
  lockedHref?: string
  lockedAction?: string
}) {
  const accents = {
    indigo: "from-indigo-500/20 via-indigo-400/10",
    cyan: "from-cyan-500/20 via-cyan-400/10",
    amber: "from-amber-500/20 via-amber-400/10",
  }

  const buttonClass =
    "rounded-full bg-white px-8 py-3 text-sm font-medium text-black transition hover:bg-gray-100 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black px-8 py-10 text-center transition-all duration-300 ${
        locked ? "opacity-80" : "hover:-translate-y-1 hover:shadow-2xl"
      }`}
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${accents[accent]} to-transparent`} />

      <div className="relative z-10 space-y-6">
        <h3 className="text-2xl font-semibold tracking-tight md:text-3xl">{title}</h3>

        <p className="mx-auto max-w-md text-base text-gray-300 md:text-lg">{description}</p>

        {badge && (
          <div className="flex justify-center">
            <span className="rounded-full bg-white/10 px-4 py-1 text-sm text-gray-300">
              {badge}
            </span>
          </div>
        )}

        {locked ? (
          <div className="space-y-4">
            <p className="mx-auto flex max-w-sm items-center justify-center gap-2 rounded-lg border border-amber-500/25 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
              <Lock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {lockedReason ?? "Complete your profile to unlock"}
            </p>
            {lockedHref && (
              <div className="flex justify-center">
                <Link href={lockedHref} className={buttonClass}>
                  {lockedAction ?? "Complete profile"}
                </Link>
              </div>
            )}
          </div>
        ) : (
          <>
            {action && href && (
              <div className="flex justify-center">
                <Link href={href} className={buttonClass}>
                  {action}
                </Link>
              </div>
            )}

            {action && !href && (
              <div className="flex justify-center">
                <button onClick={onClick} className={buttonClass} disabled={!onClick}>
                  {action}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
