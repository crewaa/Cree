type ShimmerFieldProps = {
  children: React.ReactNode;
  className?: string;
  tone?: "indigo" | "cyan";
};

const toneClasses = {
  indigo: {
    orbA: "bg-cyan-400/10",
    orbB: "bg-indigo-500/12",
    beam: "from-transparent via-cyan-300/10 to-transparent",
    grid: "[background-image:linear-gradient(rgba(255,255,255,0.032)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.032)_1px,transparent_1px)]",
  },
  cyan: {
    orbA: "bg-cyan-300/10",
    orbB: "bg-sky-500/11",
    beam: "from-transparent via-sky-200/9 to-transparent",
    grid: "[background-image:linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)]",
  },
};

export default function ShimmerField({
  children,
  className = "",
  tone = "indigo",
}: ShimmerFieldProps) {
  const palette = toneClasses[tone];

  return (
    <div
      className={`relative isolate overflow-hidden rounded-[2rem] border border-white/6 bg-white/[0.018] ${className}`}
    >
      <div className="pointer-events-none absolute inset-0">
        <div
          className={`absolute -left-20 top-0 h-48 w-48 rounded-full blur-3xl landing-aurora-drift ${palette.orbA}`}
        />
        <div
          className={`absolute right-0 top-1/3 h-64 w-64 rounded-full blur-3xl landing-aurora-drift-reverse ${palette.orbB}`}
        />
        <div
          className={`absolute inset-y-[-20%] left-[-35%] w-[55%] -skew-x-12 bg-gradient-to-r ${palette.beam} blur-3xl landing-shimmer-sweep`}
        />
        <div
          className={`absolute inset-0 bg-[size:42px_42px] ${palette.grid} opacity-25 [mask-image:radial-gradient(circle_at_center,black,transparent_82%)]`}
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.08),transparent_45%),linear-gradient(180deg,rgba(255,255,255,0.03),transparent_28%,rgba(255,255,255,0.015))]" />
      </div>

      <div className="relative z-10">{children}</div>
    </div>
  );
}
