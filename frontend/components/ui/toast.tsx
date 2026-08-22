"use client"

/**
 * Toasts.
 *
 * Replaces the native `alert()` calls that were used to report save failures.
 * `alert()` blocks the main thread, can't be styled, and reads as unfinished
 * software the moment a user sees one.
 *
 * Announced via an aria-live region so screen readers get the message too.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react"

type ToastKind = "success" | "error" | "info"

interface Toast {
  id: number
  kind: ToastKind
  message: string
}

interface ToastApi {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastApi>({
  success: () => {},
  error: () => {},
  info: () => {},
})

const AUTO_DISMISS_MS = 6000

const STYLES: Record<ToastKind, { wrap: string; Icon: typeof Info }> = {
  success: {
    wrap: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
    Icon: CheckCircle2,
  },
  error: {
    wrap: "border-red-500/30 bg-red-500/10 text-red-200",
    Icon: AlertCircle,
  },
  info: {
    wrap: "border-white/15 bg-white/[0.06] text-gray-200",
    Icon: Info,
  },
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const push = useCallback((kind: ToastKind, message: string) => {
    setToasts((prev) => [...prev, { id: Date.now() + Math.random(), kind, message }])
  }, [])

  const api: ToastApi = {
    success: useCallback((m: string) => push("success", m), [push]),
    error: useCallback((m: string) => push("error", m), [push]),
    info: useCallback((m: string) => push("info", m), [push]),
  }

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="pointer-events-none fixed bottom-6 right-6 z-[100] flex w-full max-w-sm flex-col gap-3"
        role="status"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((t) => (
          <ToastItem
            key={t.id}
            toast={t}
            onDismiss={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
          />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const { wrap, Icon } = STYLES[toast.kind]

  useEffect(() => {
    const timer = setTimeout(onDismiss, AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-md ${wrap}`}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p className="flex-1 text-sm">{toast.message}</p>
      <button
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="rounded p-0.5 opacity-60 transition hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
