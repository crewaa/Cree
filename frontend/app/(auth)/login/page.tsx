"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { useRouter } from "next/navigation"
import { login } from "@/lib/auth"
import { errorMessage } from "@/lib/types"
import { SLOW_REQUEST_MESSAGE, useSlowRequestHint } from "@/lib/slow-request"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FadeIn } from "@/components/motion/fade-in"
import Link from "next/link"
import { GoogleAuthButton } from "../../../components/auth/google-signup-button"


export default function LoginPage() {

  const router = useRouter()
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const slow = useSlowRequestHint(loading)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError("")
    setLoading(true)

    const form = e.currentTarget
    // Trimmed here as well as on the server: a trailing space pasted from a
    // password manager should never read as "wrong email".
    const email = (form.elements.namedItem("email") as HTMLInputElement).value.trim()
    const password = (form.elements.namedItem("password") as HTMLInputElement).value

    try {
      const data = await login({ email, password })

      localStorage.setItem("access_token", data.access_token)

      router.push(
        data.role === "ADMIN"
          ? "/dashboard/admin"
          : data.role === "BRAND"
          ? "/dashboard/brand"
          : "/dashboard/influencer"
      )
    } catch (err) {
      // Previously unhandled: a failed login threw into an unhandled promise
      // rejection and the form silently did nothing. `errorMessage` also turns
      // FastAPI's 422 validation array into a sentence.
      setError(errorMessage(err, "Login failed. Please try again."))
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
          Welcome back
        </h1>
        <p className="text-sm text-gray-400">
          Log in to continue to your account
        </p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="email" className="text-gray-300">Email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
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
            autoComplete="current-password"
            required
            className="bg-white/5 border-white/10 text-white focus-visible:ring-white/20"
          />
        </div>

        {error && (
          <p className="text-sm text-red-400" role="alert">
            {error}
          </p>
        )}

        <Button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white mt-2 disabled:opacity-50"
        >
          {loading ? "Logging in…" : "Login"}
        </Button>

        {slow && (
          <p className="text-center text-xs text-gray-400" role="status">
            {SLOW_REQUEST_MESSAGE}
          </p>
        )}
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
        <GoogleAuthButton />
        </div>
      </div>
    </Card>
    <p className="mt-6 text-center text-sm text-gray-400">
      Don&apos;t have an account?{" "}
      <Link 
        href="/signup" 
        className="text-white font-medium hover:underline underline-offset-4"
      >
        Sign up
      </Link>
    </p>
  </div>
  </main>
  </FadeIn>
  )
}
