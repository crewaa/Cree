import Link from "next/link"
import type { Metadata } from "next"
import { FaInstagram, FaLinkedinIn } from "react-icons/fa6"
import { Bug, Handshake, Lightbulb, Mail, Megaphone, ShieldCheck } from "lucide-react"

export const metadata: Metadata = {
  title: "Contact — Crewaa",
  description: "Get in touch with the Crewaa team. We'd love to hear from you.",
}

export default function ContactPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-3xl px-6 py-20">

        {/* Back */}
        <Link href="/" className="text-sm text-gray-500 hover:text-white transition-colors mb-10 inline-block">
          ← Back to home
        </Link>

        <h1 className="text-4xl font-bold tracking-tight mb-2">Contact Us</h1>
        <p className="text-sm text-gray-500 mb-12">We&apos;re happy to hear from you.</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">

          {/* Email card */}
          <section className="bg-white/5 border border-white/10 rounded-2xl p-8">
            <h2 className="mb-2 flex items-center gap-2 text-xl font-semibold text-white"><Mail className="h-5 w-5" /> Email</h2>
            <p className="text-gray-400 mb-4">
              For any questions, feedback, partnership inquiries, or support — just drop us an email.
              We try to respond within 1–2 business days.
            </p>
            <a
              href="mailto:crewaainfo@gmail.com"
              className="inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 font-medium text-lg transition-colors"
            >
              crewaainfo@gmail.com
            </a>
          </section>

          {/* Use cases */}
          <section>
            <h2 className="text-xl font-semibold text-white mb-4">When to reach out</h2>
            <ul className="space-y-3">
              {[
                { Icon: Handshake, label: "Partnership & collaboration opportunities" },
                { Icon: Bug, label: "Bug reports or technical issues" },
                { Icon: Lightbulb, label: "Feature requests or product feedback" },
                { Icon: ShieldCheck, label: "Account or privacy-related concerns" },
                { Icon: Megaphone, label: "Press, media, or investor inquiries" },
              ].map(({ Icon, label }) => (
                <li key={label} className="flex items-start gap-3 text-gray-300">
                  <Icon className="h-4 w-4 shrink-0 text-cyan-300/80" aria-hidden="true" />
                  <span>{label}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Social */}
          <section>
            <h2 className="text-xl font-semibold text-white mb-4">Find us on social</h2>
            <div className="flex gap-5">
              <a
                href="https://www.instagram.com/cre_waa/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-gray-400 hover:text-pink-400 transition-colors"
                aria-label="Instagram"
              >
                <FaInstagram className="h-5 w-5" />
                <span className="text-sm">@cre_waa</span>
              </a>
              <a
                href="https://www.linkedin.com/in/crewaa-ai-a519953a2/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-gray-400 hover:text-blue-400 transition-colors"
                aria-label="LinkedIn"
              >
                <FaLinkedinIn className="h-5 w-5" />
                <span className="text-sm">Crewaa on LinkedIn</span>
              </a>
            </div>
          </section>

        </div>
      </div>
    </main>
  )
}
