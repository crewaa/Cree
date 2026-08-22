"use client"

import { Suspense, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { setPassword } from "@/lib/auth"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FadeIn } from "@/components/motion/fade-in"
import { errorMessage } from "@/lib/types"

function SetPasswordForm() {
  const router = useRouter()
  const params = useSearchParams()

  const setupToken = params.get("token") ?? ""
  const email = params.get("email") ?? ""

  const [password, setPasswordValue] = useState("")
  const [confirm, setConfirm] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")

    if (password.length < 8) {
      setError("Password must be at least 8 characters.")
      return
    }

    if (password !== confirm) {
      setError("Passwords do not match.")
      return
    }

    setLoading(true)
    try {
      const data = await setPassword({ setup_token: setupToken, password })
      localStorage.setItem("access_token", data.access_token)
      router.push(data.role === "BRAND" ? "/dashboard/brand" : "/dashboard/influencer")
    } catch (err) {
      setError(errorMessage(err, "Something went wrong. Please try again."))
    } finally {
      setLoading(false)
    }
  }

  return (
    <FadeIn>
      <main className="min-h-screen flex items-center justify-center px-6 bg-black">
        <div className="flex flex-col w-full max-w-sm">
          <Card className="w-full max-w-sm bg-[#111318] border-white/10 p-8">
            {/* Header */}
            <div className="space-y-2 mb-6">
              <h1 className="text-2xl font-semibold text-white tracking-tight">
                Set your password
              </h1>
              <p className="text-sm text-gray-400">
                Create a password so you can log in with email next time.
              </p>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
              {/* Email — read-only */}
              <div className="space-y-2">
                <Label className="text-gray-300">Email</Label>
                <Input
                  value={email}
                  readOnly
                  className="bg-white/5 border-white/10 text-gray-400 cursor-not-allowed"
                />
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-gray-300">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPasswordValue(e.target.value)}
                  className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus-visible:ring-white/20"
                  required
                />
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirm" className="text-gray-300">
                  Confirm password
                </Label>
                <Input
                  id="confirm"
                  type="password"
                  placeholder="Repeat your password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className="bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus-visible:ring-white/20"
                  required
                />
              </div>

              {/* Error */}
              {error && (
                <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white mt-2 disabled:opacity-60"
              >
                {loading ? "Saving..." : "Set password & continue"}
              </Button>
            </form>
          </Card>
        </div>
      </main>
    </FadeIn>
  )
}

export default function SetPasswordPage() {
  return (
    <Suspense>
      <SetPasswordForm />
    </Suspense>
  )
}
