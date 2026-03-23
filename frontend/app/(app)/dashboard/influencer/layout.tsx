export default function InfluencerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
 

  return (
    <div className="min-h-screen">
      
      <main className="p-6">{children}</main>

    </div>
  );
}
