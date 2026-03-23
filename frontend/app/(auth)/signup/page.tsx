"use client"

import { motion } from "framer-motion"
import Link from "next/link"

const roles = [
  {
    title: "Brand",
    description: "Launch campaigns and collaborate with creators",
    href: "/signup/brand",
  },
  {
    title: "Influencer",
    description: "Get discovered and work with top brands",
    href: "/signup/influencer",
  },
]

export default function SignupPage() {
  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-xl"
      >
        <h1 className="text-2xl font-semibold text-white text-center">
          Join Crewaa
        </h1>
        <p className="mt-2 text-sm text-gray-400 text-center">
          Choose how you want to use the platform
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {roles.map((role) => (
            <Link key={role.title} href={role.href}>
              <motion.div
                whileHover={{ y: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                className="cursor-pointer rounded-xl border border-white/10 bg-[#111318] p-6 hover:border-white/20"
              >
                <h3 className="text-lg font-medium text-white">
                  {role.title}
                </h3>
                <p className="mt-2 text-sm text-gray-400">
                  {role.description}
                </p>
              </motion.div>
            </Link>
          ))}
        </div>
      </motion.div>
    </main>
  )
}
