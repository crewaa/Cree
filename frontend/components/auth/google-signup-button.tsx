"use client"

import { GoogleLogin } from "@react-oauth/google"
import { useRouter } from "next/navigation"
import axios from "axios"

type Role = "BRAND" | "INFLUENCER"

export function GoogleAuthButton({ role }: { role?: Role }) {
  const router = useRouter()

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

            const res = await axios.post(
              `${process.env.NEXT_PUBLIC_API_URL}/auth/google`,
              {
                id_token: credentialResponse.credential,
                role,
              }
            )

            const { access_token, role: userRole } = res.data

            localStorage.setItem("access_token", access_token)

            router.push(
              userRole === "BRAND"
                ? "/dashboard/brand"
                : "/dashboard/influencer"
            )
          } catch (err: any) {
            console.error("Google auth failed:", err)

            const message =
              err?.response?.data?.detail ||
              err?.response?.data?.message ||
              err?.message ||
              "Google authentication failed"

            alert(message)
          }
        }}
        onError={() => alert("Google authentication failed")}
      />
        )
      }
