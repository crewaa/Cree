"use client"

import { useState } from "react"
import { FadeIn } from "@/components/motion/fade-in"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { useRouter } from "next/navigation"
import { signup } from "@/lib/auth"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Link from "next/link"
import { GoogleAuthButton } from "@/components/auth/google-signup-button"

export default function BrandSignupPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const form = e.currentTarget
    const email = (form.elements.namedItem("email") as HTMLInputElement).value
    const password = (form.elements.namedItem("password") as HTMLInputElement).value

    try {
      const data = await signup({
        email,
        password,
        role: "BRAND",
      })

      localStorage.setItem("access_token", data.access_token)
      router.push("/dashboard/brand-profile")
    } catch (err: any) {
      setError(err?.message || "Signup failed. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <FadeIn>
    <main className="min-h-screen flex items-center justify-center px-6 bg-black">
    <div className="flex flex-col w-full max-w-sm">
    <Card className="w-full max-w-sm bg-[#111318] border-white/10 p-8">
      <div className="space-y-2 mb-6">
        <h1 className="text-2xl font-semibold text-white tracking-tight">
          Create Brand Account
        </h1>
        <p className="text-sm text-gray-400">
          Sign up to continue to your account
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="email" className="text-gray-300">Email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            required
            placeholder="name@example.com"
            className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus-visible:ring-white/20"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password" className="text-gray-300">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            required
            className="bg-white/5 border-white/10 text-white focus-visible:ring-white/20"
          />
        </div>

        <Button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white mt-2 disabled:opacity-60"
        >
          {loading ? "Creating account..." : "Sign up"}
        </Button>
      </form>

      <div className="mt-6 space-y-4">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-white/10" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-[#111318] px-2 text-gray-500">Or continue with</span>
          </div>
        </div>

        <div className="ml-5">
          <GoogleAuthButton role="BRAND" />
        </div>
      </div>
    </Card>
    <p className="mt-6 text-center text-sm text-gray-400">
      Already have an account?{" "}
      <Link
        href="/login"
        className="text-white font-medium hover:underline underline-offset-4"
      >
        Log in
      </Link>
    </p>
    </div>
  </main>
  </FadeIn>
  )
}
