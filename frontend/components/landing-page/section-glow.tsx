export default function SectionGlow() {
    return (
      <div className="relative h-24">
        <div className="absolute inset-x-0 top-1/2 h-px bg-linear-to-r from-transparent via-muted-foreground/20 to-transparent" />
      </div>
    );
  }
  