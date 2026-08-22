"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowLeft, CalendarDays, IndianRupee, Loader2, Megaphone, Plus,
  Users, X,
} from "lucide-react"

import {
  Campaign, CampaignInput, closeCampaign, createCampaign, listCampaigns,
} from "@/lib/campaigns"
import { errorMessage } from "@/lib/types"
import { useToast } from "@/components/ui/toast"

const NICHES = [
  "Fitness", "Fashion", "Tech", "Gaming", "Beauty", "Food",
  "Travel", "Lifestyle", "Education", "Finance", "Health",
]

const GOALS = ["Awareness", "Sales", "Engagement"]
const TYPES = ["Sponsored Post", "Sponsored Reel", "Product Review", "Brand Ambassador"]

const EMPTY: CampaignInput = {
  name: "",
  niche: "",
  campaign_goal: "Awareness",
  campaign_type: "Sponsored Reel",
  budget_per_creator: null,
  currency: "INR",
  deliverables: [],
  deadline: null,
  brief: "",
  platform_preferences: ["instagram"],
  target_location: "",
  min_followers: null,
  creators_needed: null,
}

/**
 * Campaigns — where a brand states its real offer.
 *
 * This page exists because the AI previously had only a budget *band* to work
 * from and invented the fee, deliverables and timeline that creators saw. What
 * a brand types here is what a creator reads, verbatim.
 */
export default function CampaignsPage() {
  const router = useRouter()
  const toast = useToast()

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<CampaignInput>(EMPTY)
  const [deliverableDraft, setDeliverableDraft] = useState("")

  async function refresh() {
    try {
      setCampaigns(await listCampaigns())
    } catch (err) {
      toast.error(errorMessage(err, "Could not load your campaigns."))
    } finally {
      setLoading(false)
    }
  }

  // Inlined rather than calling `refresh()` so no state is set synchronously
  // during the effect, and so a response arriving after the user navigates away
  // is discarded instead of warning about an unmounted update.
  useEffect(() => {
    let cancelled = false

    ;(async () => {
      try {
        const data = await listCampaigns()
        if (!cancelled) setCampaigns(data)
      } catch (err) {
        if (!cancelled) toast.error(errorMessage(err, "Could not load your campaigns."))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name || !form.niche) return

    setSaving(true)
    try {
      await createCampaign({ ...form, deadline: form.deadline || null })
      toast.success("Campaign created. Creators will start seeing it.")
      setForm(EMPTY)
      setShowForm(false)
      await refresh()
    } catch (err) {
      toast.error(errorMessage(err, "Could not create the campaign."))
    } finally {
      setSaving(false)
    }
  }

  async function handleClose(campaign: Campaign) {
    try {
      await closeCampaign(campaign.id)
      toast.success(`"${campaign.name}" closed.`)
      await refresh()
    } catch (err) {
      toast.error(errorMessage(err, "Could not close the campaign."))
    }
  }

  function addDeliverable() {
    const value = deliverableDraft.trim()
    if (!value) return
    setForm((f) => ({ ...f, deliverables: [...(f.deliverables ?? []), value] }))
    setDeliverableDraft("")
  }

  const inputClass =
    "w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white placeholder-gray-500 focus:border-indigo-500/50 focus:outline-none"
  const chipClass = (active: boolean) =>
    `rounded-full border px-4 py-2 text-sm transition cursor-pointer ${
      active
        ? "border-indigo-400 bg-indigo-500/30 text-white"
        : "border-white/10 bg-white/5 text-gray-400 hover:border-white/30"
    }`

  return (
    <div className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-[-20%] h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/15 blur-[160px]" />
      </div>

      <main className="relative z-10 mx-auto max-w-5xl px-6 py-12">
        <button
          onClick={() => router.push("/dashboard/brand")}
          className="mb-8 flex items-center gap-2 text-sm text-gray-400 transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Brand Studio
        </button>

        <div className="mb-10 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">Campaigns</h1>
            <p className="mt-3 text-lg text-gray-400">
              What you&apos;re offering, in your words. Creators see these terms exactly
              as you write them.
            </p>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-medium text-black transition hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
          >
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? "Cancel" : "New campaign"}
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleCreate}
            className="mb-12 space-y-7 rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-6 md:p-8"
          >
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">
                Campaign name * <span className="text-gray-500">(only you see this)</span>
              </label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Summer Protein Launch"
                required
                className={inputClass}
              />
            </div>

            <div>
              <label className="mb-3 block text-sm font-medium text-gray-300">
                Creator niche *
              </label>
              <div className="flex flex-wrap gap-2">
                {NICHES.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setForm({ ...form, niche: n })}
                    className={chipClass(form.niche === n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Fee per creator
                </label>
                <div className="relative">
                  <IndianRupee className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
                  <input
                    type="number"
                    min={0}
                    value={form.budget_per_creator ?? ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        budget_per_creator: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                    placeholder="30000"
                    className={`${inputClass} pl-11`}
                  />
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Shown to creators exactly as entered.
                </p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Content deadline
                </label>
                <input
                  type="date"
                  value={form.deadline ?? ""}
                  onChange={(e) => setForm({ ...form, deadline: e.target.value || null })}
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">
                Deliverables
              </label>
              <div className="flex gap-2">
                <input
                  value={deliverableDraft}
                  onChange={(e) => setDeliverableDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      addDeliverable()
                    }
                  }}
                  placeholder="1x Reel (45s)"
                  className={inputClass}
                />
                <button
                  type="button"
                  onClick={addDeliverable}
                  className="shrink-0 rounded-xl border border-white/10 px-4 text-sm text-gray-300 transition hover:border-white/30 hover:text-white"
                >
                  Add
                </button>
              </div>
              {!!form.deliverables?.length && (
                <ul className="mt-3 flex flex-wrap gap-2">
                  {form.deliverables.map((d, i) => (
                    <li
                      key={`${d}-${i}`}
                      className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-gray-300"
                    >
                      {d}
                      <button
                        type="button"
                        aria-label={`Remove ${d}`}
                        onClick={() =>
                          setForm({
                            ...form,
                            deliverables: form.deliverables!.filter((_, j) => j !== i),
                          })
                        }
                        className="opacity-60 transition hover:opacity-100"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <label className="mb-3 block text-sm font-medium text-gray-300">Goal</label>
                <div className="flex flex-wrap gap-2">
                  {GOALS.map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => setForm({ ...form, campaign_goal: g })}
                      className={chipClass(form.campaign_goal === g)}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="mb-3 block text-sm font-medium text-gray-300">
                  Collaboration type
                </label>
                <div className="flex flex-wrap gap-2">
                  {TYPES.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setForm({ ...form, campaign_type: t })}
                      className={chipClass(form.campaign_type === t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">Location</label>
                <input
                  value={form.target_location ?? ""}
                  onChange={(e) => setForm({ ...form, target_location: e.target.value })}
                  placeholder="Mumbai"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Min. followers
                </label>
                <input
                  type="number"
                  min={0}
                  value={form.min_followers ?? ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      min_followers: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                  placeholder="10000"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-300">
                  Creators needed
                </label>
                <input
                  type="number"
                  min={1}
                  value={form.creators_needed ?? ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      creators_needed: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                  placeholder="3"
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-300">Brief</label>
              <textarea
                value={form.brief ?? ""}
                onChange={(e) => setForm({ ...form, brief: e.target.value })}
                rows={3}
                placeholder="What should the creator actually make? Any must-haves?"
                className={inputClass}
              />
            </div>

            <button
              type="submit"
              disabled={saving || !form.name || !form.niche}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 py-4 text-lg font-semibold text-white transition hover:from-indigo-500 hover:to-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving && <Loader2 className="h-5 w-5 animate-spin" />}
              Create campaign
            </button>
          </form>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            <span className="sr-only">Loading campaigns…</span>
          </div>
        ) : campaigns.length === 0 ? (
          <div className="py-20 text-center">
            <Megaphone className="mx-auto mb-4 h-10 w-10 text-gray-600" aria-hidden="true" />
            <p className="text-xl text-gray-400">No campaigns yet</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-gray-500">
              Create one and creators will see your actual fee, deliverables and deadline —
              no estimates.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {campaigns.map((c) => (
              <div
                key={c.id}
                className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-[#080B14] p-6 transition hover:border-white/20"
              >
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-white">{c.name}</h2>
                    <p className="mt-1 text-sm text-gray-400">
                      {c.niche} · {c.campaign_type} · {c.campaign_goal}
                    </p>
                  </div>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${
                      c.status === "active"
                        ? "border-emerald-500/30 bg-emerald-500/15 text-emerald-300"
                        : "border-white/15 bg-white/5 text-gray-400"
                    }`}
                  >
                    {c.status}
                  </span>
                </div>

                <div className="mb-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
                  {c.budget_per_creator != null && (
                    <span className="flex items-center gap-1.5 text-emerald-300">
                      <IndianRupee className="h-3.5 w-3.5" />
                      {c.budget_per_creator.toLocaleString()} per creator
                    </span>
                  )}
                  {c.deadline && (
                    <span className="flex items-center gap-1.5 text-gray-300">
                      <CalendarDays className="h-3.5 w-3.5" />
                      Due {new Date(c.deadline).toLocaleDateString()}
                    </span>
                  )}
                  <span className="flex items-center gap-1.5 text-gray-300">
                    <Users className="h-3.5 w-3.5" />
                    {c.interested_count} interested
                  </span>
                </div>

                {!!c.deliverables?.length && (
                  <ul className="mb-4 flex flex-wrap gap-2">
                    {c.deliverables.map((d, i) => (
                      <li
                        key={`${d}-${i}`}
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-1 text-xs text-gray-300"
                      >
                        {d}
                      </li>
                    ))}
                  </ul>
                )}

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => router.push("/dashboard/brand/interested")}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-300 transition hover:border-white/25 hover:text-white"
                  >
                    View responses
                  </button>
                  {c.status === "active" && (
                    <button
                      onClick={() => handleClose(c)}
                      className="rounded-lg border border-white/10 px-3 py-2 text-sm text-gray-400 transition hover:border-red-500/30 hover:text-red-300"
                    >
                      Close campaign
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
