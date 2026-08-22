"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  getAdminUsers,
  deleteAdminUser,
  createAdminUser,
  AdminUserListItem,
  PaginatedUsers,
} from "@/lib/admin"
import { errorMessage } from "@/lib/types"
import {
  Users, Search, Plus, Trash2, Eye, ChevronLeft, ChevronRight, Check,
  X, Loader2, ShieldCheck,
} from "lucide-react"
import { useToast } from "@/components/ui/toast"

type RoleFilter = "" | "INFLUENCER" | "BRAND"

export default function AdminUsersPage() {
  const router = useRouter()
  const toast = useToast()
  const [data, setData] = useState<PaginatedUsers | null>(null)
  const [loading, setLoading] = useState(true)
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("")
  const [search, setSearch] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [page, setPage] = useState(1)
  const pageSize = 15

  // Delete modal
  const [deleteTarget, setDeleteTarget] = useState<AdminUserListItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Create modal
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ email: "", password: "", role: "INFLUENCER" })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState("")

  /**
   * Reload the list. Kept for the callers that need it directly — deleting or
   * creating a user re-reads the page they are looking at.
   *
   * It no longer flips `loading` itself. Doing so made every caller's first act
   * a synchronous state write, which inside an effect costs an extra render
   * pass; the spinner is now owned by whoever triggers the change.
   */
  const fetchUsers = useCallback(async () => {
    try {
      const res = await getAdminUsers({
        role: roleFilter || undefined,
        search: search || undefined,
        page,
        page_size: pageSize,
      })
      setData(res)
    } catch (err) {
      console.error("Failed to fetch users:", err)
    } finally {
      setLoading(false)
    }
  }, [roleFilter, search, page])

  // `loading` starts true, and the handlers below set it before changing a
  // filter, so the effect never has to write state synchronously.
  useEffect(() => {
    let cancelled = false

    ;(async () => {
      try {
        const res = await getAdminUsers({
          role: roleFilter || undefined,
          search: search || undefined,
          page,
          page_size: pageSize,
        })
        if (!cancelled) setData(res)
      } catch (err) {
        console.error("Failed to fetch users:", err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [roleFilter, search, page])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setPage(1)
    setSearch(searchInput)
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteAdminUser(deleteTarget.id)
      setDeleteTarget(null)
      fetchUsers()
    } catch (err) {
      // Previously console-only: the modal simply stopped with no explanation.
      toast.error(errorMessage(err, "Could not delete this user. Please try again."))
    } finally {
      setDeleting(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    setCreateError("")
    try {
      await createAdminUser(createForm)
      setShowCreate(false)
      setCreateForm({ email: "", password: "", role: "INFLUENCER" })
      fetchUsers()
    } catch (err) {
      setCreateError(errorMessage(err, "Failed to create user"))
    } finally {
      setCreating(false)
    }
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  const roleTabs: { label: string; value: RoleFilter }[] = [
    { label: "All Users", value: "" },
    { label: "Creators", value: "INFLUENCER" },
    { label: "Brands", value: "BRAND" },
  ]

  const roleColors: Record<string, string> = {
    INFLUENCER: "bg-cyan-500/20 text-cyan-300",
    BRAND: "bg-amber-500/20 text-amber-300",
    ADMIN: "bg-emerald-500/20 text-emerald-300",
  }

  return (
    <div className="relative relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/8 blur-[160px]" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-6 py-10">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <button
                onClick={() => router.push("/dashboard/admin")}
                className="text-gray-400 hover:text-white transition cursor-pointer"
              >
                ← Back
              </button>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight flex items-center gap-3">
              <Users className="h-7 w-7 text-indigo-400" />
              User Management
            </h1>
            <p className="text-gray-400 mt-1">
              {data ? `${data.total} total users` : "Loading..."}
            </p>
          </div>

          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium hover:bg-indigo-500 transition cursor-pointer"
          >
            <Plus className="h-4 w-4" /> Add User
          </button>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          {/* Role Tabs */}
          <div className="flex gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
            {roleTabs.map((tab) => (
              <button
                key={tab.value}
                onClick={() => { setLoading(true); setRoleFilter(tab.value); setPage(1); }}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition cursor-pointer ${
                  roleFilter === tab.value
                    ? "bg-white/15 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search */}
          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by email or ID..."
                className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
            <button
              type="submit"
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium hover:bg-white/10 transition cursor-pointer"
            >
              Search
            </button>
            {search && (
              <button
                type="button"
                onClick={() => { setLoading(true); setSearch(""); setSearchInput(""); setPage(1); }}
                className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 hover:bg-white/10 transition cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </form>
        </div>

        {/* Table */}
        <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Profile
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Joined
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="border-b border-white/5">
                      {[...Array(7)].map((_, j) => (
                        <td key={j} className="px-6 py-4">
                          <div className="h-4 w-24 animate-pulse rounded bg-white/10" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : data?.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-16 text-center text-gray-500">
                      No users found
                    </td>
                  </tr>
                ) : (
                  data?.items.map((user) => (
                    <tr
                      key={user.id}
                      className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="px-6 py-4 text-sm font-mono text-gray-400">
                        #{user.id}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium">
                        {user.email}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${roleColors[user.role] || "bg-gray-500/20 text-gray-300"}`}>
                          {user.role === "INFLUENCER" ? "Creator" : user.role === "BRAND" ? "Brand" : "Admin"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {user.role === "ADMIN" ? (
                          <span className="text-gray-500">—</span>
                        ) : user.has_profile ? (
                          <span className="flex items-center gap-1 text-emerald-400"><Check className="h-3.5 w-3.5" /> Completed</span>
                        ) : (
                          <span className="text-amber-400">Incomplete</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {user.is_active ? (
                          <span className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-emerald-400" />
                            Active
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-gray-500">
                            <span className="h-2 w-2 rounded-full bg-gray-500" />
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-400">
                        {new Date(user.created_at).toLocaleDateString(undefined, {
                          year: "numeric", month: "short", day: "numeric",
                        })}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => router.push(`/dashboard/admin/users/${user.id}`)}
                            className="rounded-lg p-2 text-gray-400 hover:bg-white/10 hover:text-white transition cursor-pointer"
                            title="View details"
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          {user.role !== "ADMIN" && (
                            <button
                              onClick={() => setDeleteTarget(user)}
                              className="rounded-lg p-2 text-gray-400 hover:bg-red-500/20 hover:text-red-400 transition cursor-pointer"
                              title="Delete user"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-white/10 px-6 py-4">
              <p className="text-sm text-gray-400">
                Page {page} of {totalPages}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => { setLoading(true); setPage(Math.max(1, page - 1)) }}
                  disabled={page <= 1}
                  className="rounded-lg border border-white/10 p-2 hover:bg-white/10 transition disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => { setLoading(true); setPage(Math.min(totalPages, page + 1)) }}
                  disabled={page >= totalPages}
                  className="rounded-lg border border-white/10 p-2 hover:bg-white/10 transition disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0E1220] p-8">
            <h2 className="text-xl font-semibold mb-2">Delete User</h2>
            <p className="text-gray-400 mb-2">
              Are you sure you want to delete this user? This action is <span className="text-red-400 font-medium">irreversible</span>.
            </p>
            <div className="my-4 rounded-xl border border-white/10 bg-white/5 p-4">
              <p className="text-sm">
                <span className="text-gray-400">Email:</span>{" "}
                <span className="font-medium">{deleteTarget.email}</span>
              </p>
              <p className="text-sm mt-1">
                <span className="text-gray-400">Role:</span>{" "}
                <span className="font-medium">{deleteTarget.role}</span>
              </p>
              <p className="text-sm mt-1">
                <span className="text-gray-400">ID:</span>{" "}
                <span className="font-mono">#{deleteTarget.id}</span>
              </p>
            </div>
            <p className="text-xs text-red-400/80 mb-6">
              All associated data (profiles, Instagram, YouTube, saved creators) will be permanently deleted.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteTarget(null)}
                className="rounded-xl border border-white/10 px-5 py-2.5 text-sm font-medium hover:bg-white/10 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-2 rounded-xl bg-red-600 px-5 py-2.5 text-sm font-medium hover:bg-red-500 transition disabled:opacity-50 cursor-pointer"
              >
                {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
                Delete User
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create User Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#0E1220] p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">Add New User</h2>
              <button
                onClick={() => { setShowCreate(false); setCreateError(""); }}
                className="rounded-lg p-1 hover:bg-white/10 transition cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  required
                  value={createForm.email}
                  onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  placeholder="user@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  placeholder="Min. 6 characters"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Role
                </label>
                <div className="flex gap-3">
                  {["INFLUENCER", "BRAND"].map((r) => (
                    <button
                      key={r}
                      type="button"
                      onClick={() => setCreateForm({ ...createForm, role: r })}
                      className={`flex-1 rounded-xl border px-4 py-2.5 text-sm font-medium transition cursor-pointer ${
                        createForm.role === r
                          ? "border-indigo-500 bg-indigo-500/20 text-white"
                          : "border-white/10 bg-white/5 text-gray-400 hover:bg-white/10"
                      }`}
                    >
                      {r === "INFLUENCER" ? "Creator" : "Brand"}
                    </button>
                  ))}
                </div>
              </div>

              {createError && (
                <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
                  {createError}
                </div>
              )}

              <button
                type="submit"
                disabled={creating}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium hover:bg-indigo-500 transition disabled:opacity-50 cursor-pointer"
              >
                {creating && <Loader2 className="h-4 w-4 animate-spin" />}
                Create User
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
