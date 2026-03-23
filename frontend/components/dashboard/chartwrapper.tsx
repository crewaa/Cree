function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
      <div className="rounded-xl border p-4">
        <h3 className="mb-4 font-semibold">{title}</h3>
        <div className="h-64">{children}</div>
      </div>
    )
  }
  
export default ChartCard; 