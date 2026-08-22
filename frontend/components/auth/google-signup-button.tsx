"use client"

import { GoogleLogin } from "@react-oauth/google"
import { useRouter } from "next/navigation"
import { api } from "@/lib/axios"
import { errorMessage } from "@/lib/types"
import { useToast } from "@/components/ui/toast"

type Role = "BRAND" | "INFLUENCER"

export function GoogleAuthButton({ role }: { role?: Role }) {
  const router = useRouter()
  const toast = useToast()

  return (
    <GoogleLogin
        theme="outline"
        size="large"
        text="continue_with"
        shape="rectangular"
        logo_alignment="left"
        width={280}
        onSuccess={async (credentialResponse) => {
          try {
            if (!credentialResponse.credential) {
              throw new Error("Missing Google credential")
            }

            const res = await api.post("/auth/google", {
              id_token: credentialResponse.credential,
              role,
            })

            const data = res.data

            // New user (or existing Google-only user) — needs to set a password
            if (data.needs_password) {
              const params = new URLSearchParams({
                token: data.setup_token,
                email: data.email,
              })
              router.push(`/set-password?${params.toString()}`)
              return
            }

            // Returning user who already has a password — go straight to dashboard
            localStorage.setItem("access_token", data.access_token)
            router.push(
              data.role === "BRAND"
                ? "/dashboard/brand"
                : "/dashboard/influencer"
            )
          } catch (err) {
            console.error("Google auth failed:", err)
            toast.error(errorMessage(err, "Google authentication failed"))
          }
        }}
        onError={() => toast.error("Google authentication failed")}
      />
        )
      }
