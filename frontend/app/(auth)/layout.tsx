export default function AuthPageLayout({
    children,
  }: {
    children: React.ReactNode
  }) {
    return (
        <div className="bg-[#0B0D10] text-[#E5E7EB]">
          {children}
        </div>
    )
  }
  