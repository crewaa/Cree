export default function SectionGlow() {
  return (
    <div className="relative h-28 overflow-hidden">
      <div className="absolute inset-x-0 top-1/2 h-px bg-gradient-to-r from-transparent via-white/14 to-transparent" />
      <div className="absolute left-1/2 top-1/2 h-20 w-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-300/8 blur-3xl" />
      <div className="absolute left-1/2 top-1/2 h-10 w-36 -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-400/10 blur-2xl" />
      <div className="absolute left-1/2 top-1/2 h-px w-40 -translate-x-1/2 -translate-y-1/2 bg-gradient-to-r from-transparent via-cyan-100/50 to-transparent" />
    </div>
  );
}
