import axios from "axios"

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  withCredentials: true,
})

/**
 * Error thrown for every failed API call.
 *
 * The previous implementation threw a bare `Error(detail)`, which discarded the
 * HTTP status — so callers could not tell a 429 (rate limited, worth retrying)
 * from a 500 (broken), and every page's `err?.response?.data?.detail` lookup was
 * reading a property that no longer existed.
 */
export class ApiError extends Error {
  status: number | null
  detail: string

  constructor(message: string, status: number | null) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.detail = message
  }
}

// Attach the bearer token. Registered before the response interceptor so the
// ordering reads in request → response order.
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

/**
 * Turn FastAPI's `detail` into a sentence a person can read.
 *
 * For normal errors `detail` is a string. For 422 validation errors it is an
 * ARRAY of objects like `{loc: ["body","email"], msg: "value is not a valid
 * email address", type: "value_error"}`. That array used to be passed straight
 * through as the error message, so users saw `[object Object]` instead of what
 * was wrong with their input.
 */
function readableDetail(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item
        if (item && typeof item === "object") {
          const { loc, msg } = item as { loc?: unknown[]; msg?: string }
          if (!msg) return null
          // Drop the "body"/"query" prefix and name the offending field.
          const field = Array.isArray(loc)
            ? loc.filter((p) => p !== "body" && p !== "query").join(" ")
            : ""
          return field ? `${field}: ${msg}` : msg
        }
        return null
      })
      .filter(Boolean) as string[]

    if (messages.length) return messages.join(". ")
  }

  return "Something went wrong"
}

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response) {
      const status = error.response.status
      const detail = readableDetail(error.response.data?.detail)

      // 401 means the token is missing, expired or rejected. Clear it so the
      // app does not keep retrying with a dead credential.
      if (status === 401 && typeof window !== "undefined") {
        localStorage.removeItem("access_token")
      }

      throw new ApiError(detail, status)
    }

    if (error.request) {
      throw new ApiError("Backend not reachable", null)
    }

    throw error
  }
)
