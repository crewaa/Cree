import Link from "next/link"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Privacy Policy — Crewaa",
  description: "Learn how Crewaa collects, uses, and protects your personal information.",
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <div className="mx-auto max-w-3xl px-6 py-20">

        {/* Back */}
        <Link href="/" className="text-sm text-gray-500 hover:text-white transition-colors mb-10 inline-block">
          ← Back to home
        </Link>

        <h1 className="text-4xl font-bold tracking-tight mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-500 mb-12">Last updated: April 2025</p>

        <div className="space-y-10 text-gray-300 leading-relaxed">

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. Information We Collect</h2>
            <p>
              When you sign up for Crewaa, we collect information you provide directly — such as your name,
              email address, role (brand or creator), and profile details. If you sign in with Google, we
              receive your name and email from Google&apos;s OAuth service. We do not access your Google account
              beyond what is required for authentication.
            </p>
            <p className="mt-3">
              We also collect information automatically as you use the platform, including usage data,
              device information, and log data such as your IP address and pages visited. This helps us
              improve the product and debug issues.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. How We Use Your Information</h2>
            <ul className="list-disc list-inside space-y-2">
              <li>To create and manage your account</li>
              <li>To connect brands with the right creators using our AI-powered matching</li>
              <li>To generate insights and analytics about creator profiles</li>
              <li>To send important product updates or notifications (not spam)</li>
              <li>To improve and personalize your experience on Crewaa</li>
              <li>To comply with legal obligations</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">3. Sharing Your Information</h2>
            <p>
              We do not sell, rent, or share your personal data with third parties for their marketing
              purposes. We may share data with trusted service providers (such as cloud hosting and
              analytics tools) solely to operate the platform. These providers are bound by confidentiality
              agreements and are not permitted to use your data for any other purpose.
            </p>
            <p className="mt-3">
              Creator profile data (such as social media usernames and public metrics) may be visible to
              brands using the platform for discovery purposes — this is core to Crewaa&apos;s functionality.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. Data Retention</h2>
            <p>
              We retain your data for as long as your account is active. You may delete your account at
              any time by contacting us at{" "}
              <a href="mailto:crewaainfo@gmail.com" className="text-indigo-400 hover:underline">
                crewaainfo@gmail.com
              </a>
              , and we will delete your personal data within 30 days, except where retention is required
              by law.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. Cookies</h2>
            <p>
              Crewaa uses minimal cookies necessary for authentication and session management. We do not
              use tracking cookies or third-party advertising cookies.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. Security</h2>
            <p>
              We take security seriously. Passwords are hashed using bcrypt and never stored in plain text.
              All data is transmitted over HTTPS. While we implement industry-standard safeguards, no
              system is completely immune to breaches and we encourage you to use a strong, unique password.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. Your Rights</h2>
            <p>
              You have the right to access, correct, or delete your personal data at any time. To exercise
              these rights, reach out to us at{" "}
              <a href="mailto:crewaainfo@gmail.com" className="text-indigo-400 hover:underline">
                crewaainfo@gmail.com
              </a>.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">8. Changes to This Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. When we do, we&apos;ll update the &quot;last
              updated&quot; date at the top of this page. Continued use of Crewaa after any changes constitutes
              your acceptance of the updated policy.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">9. Contact</h2>
            <p>
              If you have any questions about this Privacy Policy, please email us at{" "}
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
