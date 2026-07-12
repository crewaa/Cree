import Link from "next/link"
import { FaInstagram, FaLinkedinIn, FaXTwitter } from "react-icons/fa6"
import ShimmerField from "./shimmer-field"


export function LandingPageFooter() {
  return (
    <footer className="px-6 pb-8">
      <ShimmerField className="mx-auto max-w-7xl px-6 py-10 sm:px-8">
        <div className="flex flex-col items-center justify-between gap-5 md:flex-row">
          <p className="text-sm text-slate-400">
            © {new Date().getFullYear()} Crewaa. All rights reserved.
          </p>

          <div className="flex gap-6 text-sm text-slate-300">
            <Link href="/privacy" className="transition hover:text-white">
              Privacy
            </Link>
            <Link href="/terms" className="transition hover:text-white">
              Terms
            </Link>
            <Link href="/contact" className="transition hover:text-white">
              Contact
            </Link>
          </div>

          <div className="flex items-center gap-5">
            <a
              href="https://www.instagram.com/cre_waa/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 transition duration-300 hover:-translate-y-0.5 hover:text-pink-300"
              aria-label="Instagram"
            >
              <FaInstagram className="h-5 w-5" />
            </a>

            <a
              href="https://www.linkedin.com/in/crewaa-ai-a519953a2/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 transition duration-300 hover:-translate-y-0.5 hover:text-cyan-200"
              aria-label="LinkedIn"
            >
              <FaLinkedinIn className="h-5 w-5" />
            </a>

            <a
              href="https://x.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 transition duration-300 hover:-translate-y-0.5 hover:text-white"
              aria-label="X (Twitter)"
            >
              <FaXTwitter className="h-5 w-5" />
            </a>
          </div>
        </div>
      </ShimmerField>
    </footer>
  )
}
