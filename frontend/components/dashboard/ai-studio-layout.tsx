"use client"

import Link from "next/link"

export function AICard({
    title,
    description,
    action,
    badge,
    accent = "indigo",
    href,
    onClick,
  }: {
    title: string
    description: string
    action?: string
    badge?: string
    accent?: "indigo" | "cyan" | "amber"
    href?: string
    onClick?: () => void
  }) {
    const accents = {
      indigo: "from-indigo-500/20 via-indigo-400/10",
      cyan: "from-cyan-500/20 via-cyan-400/10",
      amber: "from-amber-500/20 via-amber-400/10",
    }
  
    return (
      <div className="
        relative overflow-hidden rounded-2xl
        border border-white/10
        bg-gradient-to-br from-[#0E1220] to-black
        px-8 py-10
        text-center
        transition-all duration-300
        hover:-translate-y-1 hover:shadow-2xl
      ">
        {/* Accent Glow */}
        <div
          className={`absolute inset-0 bg-gradient-to-br ${accents[accent]} to-transparent`}
        />
  
        <div className="relative z-10 space-y-6">
          <div className="flex justify-center">
            <h3 className="text-2xl md:text-3xl font-semibold tracking-tight">
              {title}
            </h3>
          </div>
  
          <p className="mx-auto max-w-md text-base md:text-lg text-gray-300">
            {description}
          </p>
  
          {badge && (
            <div className="flex justify-center">
              <span className="rounded-full bg-white/10 px-4 py-1 text-sm text-gray-300">
                {badge}
              </span>
            </div>
          )}
  
          {action && href && (
            <div className="flex justify-center">
              <Link href={href}>
                <button className="
                  rounded-full bg-white px-8 py-3
                  text-sm font-medium text-black
                  hover:bg-gray-100 transition
                  cursor-pointer
                ">
                  {action}
                </button>
              </Link>
            </div>
          )}

          {action && !href && onClick && (
            <div className="flex justify-center">
              <button
                onClick={onClick}
                className="
                  rounded-full bg-white px-8 py-3
                  text-sm font-medium text-black
                  hover:bg-gray-100 transition
                  cursor-pointer
                "
              >
                {action}
              </button>
            </div>
          )}

          {action && !href && !onClick && (
            <div className="flex justify-center">
              <button className="
                rounded-full bg-white px-8 py-3
                text-sm font-medium text-black
                hover:bg-gray-100 transition
              ">
                {action}
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }
  