export default function DarkCard({
    title,
    description,
    action,
    badge,
  }: {
    title: string
    description: string
    action?: string
    badge?: string
  }) {
    return (
      <div className="relative overflow-hidden rounded-xl border border-white/10 bg-linear-to-br from-[#111827] via-[#0B0F1A] to-black p-6 transition-all hover:-translate-y-1 hover:shadow-2xl">
        
        {/* Gold Flow Accent */}
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,transparent,rgba(234,179,8,0.18),transparent)]" />
  
        <div className="relative z-10">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">{title}</h3>
  
            {badge && (
              <span className="text-xs rounded-full bg-yellow-500/10 text-yellow-400 px-3 py-1">
                {badge}
              </span>
            )}
          </div>
  
          <p className="mt-2 text-sm text-gray-400">
            {description}
          </p>
  
          {action && (
            <button className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-700">
              {action}
            </button>
          )}
        </div>
      </div>
    )
  }
  