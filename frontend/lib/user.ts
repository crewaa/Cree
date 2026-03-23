import { api } from "./axios"

export async function getCurrentUser() {
  const res = await api.get("/users/me")
  return res.data
}
