import Link from "next/link"
import { Button } from "@/components/ui/button"
import Image from "next/image"

export function LandingPageNavbar() {
  return (
    <header className="fixed top-0 inset-x-0 z-50 backdrop-blur border-b border-white/5">
      <nav className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
        {/* Logo */}

        <Link href="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
        <Image 
            src="/Crewaa.png"   
            alt="Crewaa Logo"
            width={33}        
            height={33}
            className="shrink-0 bg-transparent"
        />
        <span className="text-lg font-bold tracking-tight">
            Crewaa
        </span>
        </Link>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-sm text-gray-300 hover:text-white transition"
          >
            Login
          </Link>

          <Link href="/signup">
          <Button className="bg-indigo-500 hover:bg-indigo-400 text-white">
            Get Started
          </Button>
          </Link>
        </div>
      </nav>
    </header>
  )
}
