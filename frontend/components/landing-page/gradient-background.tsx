export default function GradientBackground({
    children,
  }: {
    children: React.ReactNode;
  }) {
    return (
      <div className="relative overflow-hidden">
        {/* Gradient blobs */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-purple-500/30 blur-3xl" />
          <div className="absolute top-1/3 -right-32 h-96 w-96 rounded-full bg-blue-500/30 blur-3xl" />
          <div className="absolute bottom-0 left-1/4 h-96 w-96 rounded-full bg-pink-500/20 blur-3xl" />
        </div>
  
        {/* Noise overlay */}
        <div className="noise-bg" />
  
        {/* Content */}
        <div className="relative">{children}</div>
      </div>
    );
  }
  