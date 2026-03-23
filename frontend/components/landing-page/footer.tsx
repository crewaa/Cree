import Link from "next/link"
import { FaInstagram, FaLinkedinIn, FaXTwitter } from "react-icons/fa6"


export function LandingPageFooter() {
  return (
    <footer className="border-t border-white/5">
      <div className="mx-auto max-w-7xl px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-sm text-gray-500">
          © {new Date().getFullYear()} Crewaa. All rights reserved.
        </p>

        <div className="flex gap-6 text-sm text-gray-400">
          <Link href="/privacy" className="hover:text-white">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-white">
            Terms
          </Link>
          <Link href="/contact" className="hover:text-white">
            Contact
          </Link>
        </div>

         {/* Social Icons */}
         <div className="flex items-center gap-5">
          <a
            href="https://www.instagram.com/cre_waa/"
            target="_blank"
            rel="noopener noreferrer"
            className="
              text-gray-400 transition-all duration-300
              hover:text-pink-500 hover:-translate-y-1
            "
            aria-label="Instagram"
          >
            <FaInstagram className="h-5 w-5" />
          </a>

          <a
            href="https://www.linkedin.com/in/crewaa-ai-a519953a2/"
            target="_blank"
            rel="noopener noreferrer"
            className="
              text-gray-400 transition-all duration-300
              hover:text-blue-500 hover:-translate-y-1
            "
            aria-label="LinkedIn"
          >
            <FaLinkedinIn className="h-5 w-5" />
          </a>

          <a
            href="https://x.com"
            target="_blank"
            rel="noopener noreferrer"
            className="
              text-gray-400 transition-all duration-300
              hover:text-white hover:-translate-y-1
            "
            aria-label="X (Twitter)"
          >
            <FaXTwitter className="h-5 w-5" />
          </a>
        </div>
      </div>
    </footer>
  )
}
