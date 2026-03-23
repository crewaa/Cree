import { api } from "./axios"

export async function signup(data: {
  email: string
  password: string
  role: "BRAND" | "INFLUENCER"
}) {
  const res = await api.post("/auth/signup", data)
  return res.data
}

export async function login(data: {
  email: string
  password: string
}) {
  const res = await api.post("/auth/login", data)
  return res.data
}

export async function logout() {
  await api.post("/auth/logout")

  // Clear access token
  localStorage.removeItem("access_token")
}