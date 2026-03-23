import axios from "axios"

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  withCredentials: true,
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response) {
      console.error("API Error:", error.response.data)
      throw new Error(error.response.data.detail || "API Error")
    }

    if (error.request) {
      console.error("Network Error:", error.message)
      throw new Error("Backend not reachable")
    }

    throw error
  }
)

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
