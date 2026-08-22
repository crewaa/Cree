import Link from "next/link"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Terms of Service — Crewaa",
  description: "Read the Terms of Service for using the Crewaa platform.",
}

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-3xl px-6 py-20">

        {/* Back */}
        <Link href="/" className="text-sm text-gray-500 hover:text-white transition-colors mb-10 inline-block">
          ← Back to home
        </Link>

        <h1 className="text-4xl font-bold tracking-tight mb-2">Terms of Service</h1>
        <p className="text-sm text-gray-500 mb-12">Last updated: April 2025</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. Acceptance of Terms</h2>
            <p>
              By creating an account or using Crewaa in any way, you agree to be bound by these Terms of
              Service. If you do not agree to these terms, please do not use the platform.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. Who Can Use Crewaa</h2>
            <p>
              Crewaa is available to individuals and businesses who are at least 18 years of age. By signing
              up, you confirm that you meet this age requirement and that all information you provide is
              accurate and truthful.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">3. Account Responsibilities</h2>
            <p>
              You are responsible for maintaining the security of your account credentials. Crewaa is not
              liable for any loss or damage resulting from unauthorized access to your account. You must
              notify us immediately at{" "}
              <a href="mailto:crewaainfo@gmail.com" className="text-indigo-400 hover:underline">
                crewaainfo@gmail.com
              </a>{" "}
              if you suspect any unauthorized use.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. Platform Use</h2>
            <p>You agree not to:</p>
            <ul className="list-disc list-inside space-y-2 mt-3">
              <li>Use Crewaa for any unlawful purpose or in violation of any applicable laws</li>
              <li>Impersonate any person or entity, or misrepresent your affiliation with a brand or creator</li>
              <li>Attempt to gain unauthorized access to any part of the platform or its data</li>
              <li>Scrape, copy, or redistribute any content from Crewaa without written permission</li>
              <li>Submit false or misleading information about yourself or your brand</li>
              <li>Harass, abuse, or harm other users of the platform</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. Brands and Creators</h2>
            <p>
              Crewaa is a discovery and outreach platform. Any collaboration, payment, or agreement made
              between a brand and a creator through connections formed on Crewaa is entirely between those
              parties. Crewaa is not a party to, and bears no responsibility for, any deals, disputes, or
              outcomes arising from such arrangements.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. AI-Generated Content</h2>
            <p>
              Crewaa uses artificial intelligence to generate creator summaries, brand deal suggestions,
              and compatibility scores. These are provided for informational purposes only and should not
              be treated as professional advice. AI outputs may contain inaccuracies — always exercise your
              own judgment before making business decisions.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. Intellectual Property</h2>
            <p>
              All content on Crewaa — including its logo, design, software, and copy — is the property of
              Crewaa and is protected by applicable intellectual property laws. You may not use, reproduce,
              or distribute our content without prior written permission.
            </p>
            <p className="mt-3">
              You retain ownership of any content you submit to Crewaa (such as your profile information).
              By submitting it, you grant Crewaa a limited, non-exclusive license to display it on the
              platform for the purpose of facilitating brand-creator connections.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">8. Termination</h2>
            <p>
              We reserve the right to suspend or permanently terminate your account if you violate these
              Terms of Service, with or without notice. You may also close your account at any time by
              contacting us at{" "}
              <a href="mailto:crewaainfo@gmail.com" className="text-indigo-400 hover:underline">
                crewaainfo@gmail.com
              </a>.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">9. Disclaimer of Warranties</h2>
            <p>
              Crewaa is provided &quot;as is&quot; and &quot;as available&quot; without warranties of any kind, either express
              or implied. We do not guarantee that the platform will be uninterrupted, error-free, or
              free of bugs. Use of the platform is at your own risk.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">10. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, Crewaa shall not be liable for any indirect,
              incidental, special, or consequential damages arising out of or in connection with your use
              of the platform, even if we have been advised of the possibility of such damages.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">11. Changes to Terms</h2>
            <p>
              We may revise these Terms of Service from time to time. We will notify users of significant
              changes by updating the date at the top of this page. Continued use of Crewaa after changes
              are posted constitutes your acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">12. Contact</h2>
            <p>
              For any questions about these Terms, please reach out to us at{" "}
              <a href="mailto:crewaainfo@gmail.com" className="text-indigo-400 hover:underline">
                crewaainfo@gmail.com
              </a>.
            </p>
          </section>

        </div>
      </div>
    </main>
  )
}
