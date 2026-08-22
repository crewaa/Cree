# Crewaa — Product & UX Review

> **Runtime walkthrough completed 2026-08-12.** Backend and frontend run locally, seeded with an
> admin, 2 brands and 4 creators with realistic Instagram/YouTube data. Gemini/Apify/YouTube were
> stubbed with ~1.6s latency so the AI paths could be exercised without live keys.
> A real browser walked both sides: signup, login, every studio card, every form, admin console,
> and mobile at 390×844. Screenshots in `.walkthrough-shots/`.
>
> Every finding below is **✅ verified at runtime** unless marked otherwise.
> Severity: 🔴 blocks launch · 🟠 hurts credibility · 🟡 polish
>
> **UPDATE 2026-08-12 — first fix pass shipped and re-verified in the browser:**
>
> | # | Finding | Status |
> |---|---|---|
> | 1 | Profile/Analytics unreachable by URL | ✅ **FIXED** — both stay put on direct load; profile form renders its 9 fields |
> | 4 | Discovery ignored the niche | ✅ **FIXED** — Fitness campaign now ranks the Fitness creator #1 (was last) |
> | 7 | White navbar + white gutter | ✅ **FIXED** — dark shell owns the surface; `body` is `rgb(6,7,12)` on dashboards, unchanged on marketing pages |
> | 9 | 19× `GET /users/me` | ✅ **FIXED** — one fetch per page load via `SessionProvider`; skeleton replaces the blank screen |
> | — | 422 validation errors rendered as `[object Object]` | ✅ **FIXED** — `readableDetail()` turns FastAPI's array into "email: value is not a valid email address" |
> | — | `saved_at` non-portable `now()` default | ✅ **FIXED** — `CURRENT_TIMESTAMP`; 4 new schema-parity tests now compare **columns and defaults**, not just table names |
>
> Navigation also gained real links (Studio / Analytics / Profile) with lucide icons.
> Verified after: **90 backend tests pass**, migrations build with zero drift, typecheck clean,
> **0 lint errors**, 30 routes still fully guarded, mobile still 0px overflow.
>
> **Second pass:**
>
> | # | Finding | Status |
> |---|---|---|
> | 5 | Discovery results not actionable | ✅ **FIXED** — cards now carry name, verified badge, niche, location, bio, followers, subscribers, engagement %, avg likes and clickable handles. Raw database ids removed. All profile facts are read **from the database**, never from the model, so a hallucinated name can't be shown as real. |
> | 8 | Emoji icons | ✅ **FIXED on Discover** — swapped for lucide (the page where tofu boxes were observed). Remaining studio/deals/analyzer pages still use emoji. |
>
> **Third pass — the marketplace loop:**
>
> | # | Finding | Status |
> |---|---|---|
> | 2 | Invented compensation shown as fact | ✅ **FIXED** — the card now shows the brand's real **budget band** as verified, relabels the model's numbers as *Indicative fee / Indicative timeline / Suggested deliverables*, and carries a standing notice that final terms are agreed directly with the brand. `terms_are_estimated` is on the API so the UI cannot forget. |
> | 3 | Both sides dead ends | ✅ **FIXED** — creators get **"I'm interested"** (and can withdraw); brands get a **Responses** inbox with name, niche, location, followers, engagement, the creator's note and contact details. |
>
> **The anonymity asymmetry is preserved and tested:** the creator sends only an
> opportunity id and never learns the brand — attribution is resolved server-side from
> their own cached deals, which also prevents applying to an opportunity never offered
> to them. Expressing interest reveals the *creator* to the brand, because the creator
> opted in. Verified in the browser: the owning brand sees the applicant, the other
> brand sees nothing.
>
> Verified after: **102 backend tests** (12 new), 33 routes all guarded, migrations
> build with zero drift, typecheck clean, 0 lint errors.
>
> **Fourth pass — polish:**
>
> | # | Finding | Status |
> |---|---|---|
> | 6 | New creator hits a dead end | ✅ **FIXED** — studio cards are locked until a profile exists, with a "One step to go" banner and a direct CTA. Backed by `GET /users/profile-status`, which answers 200 either way so the check does not log a console error. |
> | 8 | Emoji icons | ✅ **FIXED** — **0 emoji left** across the whole frontend (was 40 across 14 files); all lucide now. |
> | — | `alert()` for errors | ✅ **FIXED** — accessible toast system with an aria-live region; all 4 call sites migrated. |
> | — | No 404 / error boundary | ✅ **FIXED** — branded `not-found.tsx` and `error.tsx` with a recovery action and error digest. |
> | — | Dead pages | ✅ **FIXED** — `/dashboard` now redirects by role (was the literal text "Landing Page"); duplicate analytics page, unrouted `creator-dashboard` and its form deleted. |
> | — | No page metadata | ✅ **FIXED** — title template, description, OpenGraph and Twitter cards, plus per-page titles. |
>
> Verified after: **102 backend tests**, 34 routes all guarded, migrations build with
> zero drift, typecheck clean, **0 lint errors**, build compiles 24 routes, secret scan clean.
> Browser-verified: new user sees the locked studio and lands on the profile form; existing
> creator sees it unlocked; `/dashboard` redirects; custom 404 renders; **zero 4xx responses**
> for a user with a profile.
>
> **Fifth pass — data hygiene:**
>
> | Item | Status |
> |---|---|
> | AI caches had no TTL | ✅ **FIXED** — `*_generated_at` was written and never read; both cached AI results now report `generated_at` and `is_stale`, and the UI shows an amber "this may not reflect your current audience" banner past the window (`AI_CACHE_STALE_AFTER_DAYS`, default 14). |
> | Instagram snapshots grew forever | ✅ **FIXED** — pruned after `SCRAPE_TTL_DAYS` (default 90, already in your `.env`). The newest snapshot is always kept, so a creator who has not scraped in a year never loses their analytics. Two tests cover both halves. |
> | Admin delete failures were silent | ✅ **FIXED** — `console.error` only; now surfaced as a toast. |
>
> Verified: **104 backend tests**, 34 routes guarded, zero schema drift, typecheck clean,
> 0 lint errors, build compiles 24 routes, secret scan clean.
>
> **Sixth pass — real campaigns (§2 root cause):**
>
> Brands now create **campaigns** stating their actual fee, deliverables and deadline.
> A creator sees those values verbatim; the AI's only job is judging fit and writing the
> description. **The model is structurally unable to state a price** — commercial keys are
> stripped from its response and the numbers are read from the campaign record, so even a
> model that tries to invent a fee cannot get one onto a creator's screen. There is a test
> that feeds a model response containing `"Rs 999,999"` and asserts the creator still sees
> the brand's ₹30,000.
>
> | Piece | Detail |
> |---|---|
> | `campaigns` table | Real fee, currency, deliverables, deadline, brief, targeting, status |
> | Campaign CRUD | Owner-scoped; a foreign campaign returns 404 rather than 403 so its existence is not disclosed |
> | Closing, not deleting | Interests reference campaigns; hard deletion would erase history people acted on |
> | Brand Deals | Sources active campaigns first; brands without one still appear via the legacy path, clearly flagged as estimates |
> | Interests | Now record `campaign_id`, so a brand sees responses per campaign |
> | Anonymity | Unchanged and re-tested: neither `brand_id` nor `campaign_id` reaches the creator |
>
> Browser-verified side by side: a campaign-backed card shows **Fee ₹30,000 / Deadline
> 3/15/2026 / Deliverables / What to expect / Why you** with no disclaimer, while a
> legacy card still shows *Indicative fee* and the estimate notice.
>
> Verified: **116 backend tests** (12 new for campaigns), 39 routes all guarded, 11 tables
> with zero drift, migrations re-runnable, typecheck clean, 0 lint errors, 25 routes build,
> 0 emoji remaining.
>
> **Seventh pass — Discovery runs on a campaign:**
>
> Discover now asks *which campaign* first. Picking one reads niche, goal, location, platforms
> and the follower minimum straight from that record, and the ad-hoc form disappears — there is
> nothing left to re-type. A brand with no campaigns, or one that wants a one-off look, still
> gets the old form behind a "Something else" option.
>
> | Piece | Detail |
> |---|---|
> | Single source of truth | With `campaign_id` the loose fields are **ignored, not merged**. A stale form value cannot quietly redirect a campaign's search, and there is never a question of which value won. |
> | `min_followers` finally applied | The brand could state a floor and every code path ignored it. Reach is now the larger of the two platform counts, not their sum, so two small accounts cannot pose as one large one. |
> | Unmeetable floors | If nobody clears the minimum, results are returned unfiltered **and say so** — an empty screen is indistinguishable from a broken one. |
> | Never-scraped creators | Pass the floor. No snapshot means no information, not a small audience; excluding them would hide every new signup from every campaign with a minimum. |
> | Ownership | Another brand's `campaign_id` is a **404**, matching `/campaigns`. |
> | Attribution | Results carry `criteria_source` and the campaign name, so a shortlist is never mistaken for one built against a different brief. |
>
> Browser-verified with a Fitness campaign at a 100k floor: the 142.5K Fitness creator ranked,
> while the 89.3K and 23.8K creators were dropped by the floor; the ad-hoc path returned all
> four with no floor; the second brand could not see the campaign at all.
>
> Also fixed: the navbar lit up two items at once on any page under `/dashboard/brand`, because
> the studio's href is a prefix of every page below it. The most specific link now wins.
>
> Verified: **124 backend tests** (8 new), 39 routes all guarded, typecheck clean, 0 lint errors,
> 25 routes build.
>
> **Eighth pass — streaming and niche-ordered deals (§11):**
>
> | Piece | Detail |
> |---|---|
> | `POST /ai/brand-deals/stream` | NDJSON, one complete card per line, then a `done` line. Late failures arrive in-band as an `error` line — after the first byte there is no status code left to change. |
> | One generator, two endpoints | Streaming and batch both run `_assess_opportunities` + `_public_opportunities`, so the anonymity and real-terms guarantees cannot drift between them. The anonymity test asserts on the streamed bytes. |
> | Partial results survive | A failure on the fourth brand no longer discards the three that succeeded. |
> | Client disconnect cancels the run | Closing the page cancels the outstanding Gemini calls instead of paying for a screen nobody is looking at. |
> | Deals ordered by the creator's niche | The run is capped, so this decides what a creator *sees*, not just the order. Ordering, not filtering — a creator in a thin niche still gets results. |
>
> Measured end to end with six campaigns at a concurrency of two: **first card at 1.68s, last at
> 4.97s** — the creator previously waited the full 4.97s for anything at all. A direct trace of
> the stream for a Fitness creator returned both Fitness campaigns first (at 1.62s) even though
> one was the *oldest* campaign and a Travel campaign was the newest.
>
> Also corrected: the streaming route first opened its own database session, on the belief that
> an injected `get_db` would be closed before the body was produced. That was checked against the
> pinned FastAPI 0.141 / Starlette 1.6 and found to be false — reads and the final commit both
> succeed — so it uses the shared `get_db` per rule 9, with the verification noted in the
> docstring for whoever next upgrades FastAPI.
>
> Verified: **132 backend tests** (8 new), 40 routes all guarded, typecheck clean, 0 lint errors.
>
> **Ninth pass — error tracking (§Sentry):**
>
> Wired for both the FastAPI backend and the Next.js frontend, and **inert until a DSN is
> set**, so local dev and CI need no account. Vishal supplies two DSNs; see
> `ACTION-REQUIRED.md` §6.
>
> The integration is mostly privacy plumbing, because the default settings are dangerous here:
>
> | Decision | Why |
> |---|---|
> | `include_local_variables=False` | Sentry ships every stack frame's locals by default. Ours hold the Neon password, the JWT signing key and every API key. This is the same reason loguru runs `diagnose=False`; an error tracker would have silently undone it. |
> | `send_default_pii=False` | No emails, no IPs. |
> | `before_send` scrubbing | Secrets also leak through *messages* — asyncpg puts the whole connection string in its connection errors. Redacts by key, by URL shape, by bearer pattern and by API-key prefix. |
> | Brand identity scrubbed | Anonymity is a product promise, so `brand_id` / `brand_name` are treated like passwords. |
> | Session replay off | It records the user's screen: a creator's private analytics, a brand's budget. |
> | Tracing off by default | Billed separately from errors. |
> | Scrub failure drops the event | Losing an error report beats sending an unscrubbed one. |
>
> **Verified without a Sentry account**, by pointing the real SDK at an in-process transport
> (backend) and at a fake Sentry server on localhost (frontend):
>
> - A real 500 produces **exactly one** event, tagged with the same `request_id` as the access
>   log — so an issue links to real log lines. The count is asserted, because two integrations
>   can capture the same error and doubling issues doubles the bill.
> - A crash whose frame locals held a Neon password and a Gemini key leaked **neither**.
> - A browser render crash carrying a JWT arrived at the collector as
>   `render blew up with Bearer [redacted]`.
>
> Two claims in the first draft were wrong and were corrected after measurement: the explicit
> `capture()` call is *not* what makes reporting work (sentry-sdk auto-enables a loguru
> integration, so `logger.exception` already reports — the call is belt-and-braces against log
> routing changing), and a side effect worth knowing is that every existing `logger.error(...)`
> becomes a Sentry issue once a DSN is set.
>
> Verified: **145 backend tests** (13 new), typecheck clean, build compiles 25 routes with and
> without a DSN.
>
> **DSNs installed 2026-08-13.** Two Sentry projects (`crewaa-backend`, `crewaa-frontend`);
> both DSNs are in gitignored env files and the backend now logs `Error tracking enabled` at
> boot. Delivery itself is unverified — the sandbox has no network route to Sentry — so
> `backend/scripts/verify-sentry.py` exists to prove it from a machine that does. It plants a
> fake password and API key in local scope so the same run confirms events arrive *and* that
> frame locals are not leaking.
>
> Installing the DSN surfaced a trap worth recording: `Settings` also reads `backend/.env`, so
> a plain `pytest` on a developer's machine would have initialised the **live** client and
> filed every deliberate test failure as a production issue — roughly a hundred events per run
> against a 5k/month quota. `conftest.py` now forces `SENTRY_DSN=""`, and
> `tests/test_no_live_sentry_in_tests.py` guards it. That guard was checked by sabotaging the
> override and confirming the suite goes red.
>
> **Tenth pass — prompt evals:**
>
> The gap this closes: anonymity and structure were tested, **quality was not**. A prompt edit
> or a Gemini model update could quietly make matching worse, and the first person to find out
> would be a brand who paid for a shortlist of the wrong creators.
>
> `backend/evals/` — 8 golden cases, each with a written rationale for why the expected answer
> is right. Findings are graded, and the grading is the design:
>
> | Grade | Meaning | Effect |
> |---|---|---|
> | **violation** | Damages a user: wrong-niche "High" fit, invented creator id, leaked brand name, model-stated fee | Fails the run at any rate above zero |
> | **miss** | Defensible but not what a person would pick | Moves `quality_score`; watched as a trend |
> | **malformed** | Output the parser cannot use | Fails; almost always a prompt edit |
>
> Two modes. **Replay** scores frozen responses — free, deterministic, runs in CI, and catches a
> broken prompt or parser. It *cannot* detect the model getting worse, and the README says so
> plainly. **`--live`** is the real measurement, with `--repeat N` because the model is
> stochastic and one run of one case is not evidence; it judges on the worst run, not the best.
>
> Live runs are deliberately **not** in CI: they cost quota and are non-deterministic, and a
> flaky red build teaches people to ignore the suite.
>
> **The suite is proven non-vacuous.** `tests/test_evals.py` is mostly composed of deliberately
> degraded outputs asserted to go red — a model rating everything "High" produces 4 violations
> and drops quality to 20%. One test also runs the live path with only the network stubbed and
> asserts the *real* `BRAND_CREATOR_RANKING_PROMPT` and injection guard reached the model, so
> the evals cannot drift into measuring a copy of the prompt.
>
> Honest limitation, recorded in the README and in `recorded.json` itself: the shipped fixtures
> are **hand-written, not captured from Gemini** — this environment had no network route to
> Google. One `--live --record` run from a networked machine replaces them and writes the first
> real baseline.
>
> Verified: **195 backend tests** (17 new), evals CLI green, CI wired.
>
> **Eleventh pass — sign-in and sign-up ("sometimes works, sometimes doesn't, very slow"):**
>
> Every cause below was reproduced before it was changed, then re-measured after.
>
> | Cause | Evidence before | After |
> |---|---|---|
> | bcrypt ran on the event loop | 5 concurrent sign-ins took **882ms, strictly serialised**; the loop ticked **0** times during a hash, so every other request on the worker froze too | pushed to a thread: **295ms**, overlapping |
> | Sign-up hashed *and then verified* the same password | 390ms per sign-up | **200ms** — the token is minted from the user just created |
> | `Vishal@gmail.com` != `vishal@gmail.com` | login with different case returned **401 Invalid credentials**, and a *second account* could be created for the same person | normalised on write, looked up case-insensitively so existing rows still work |
> | Two simultaneous sign-ups | **5 × HTTP 500** | 1 × 200, 4 × 400 with "please log in" |
> | Login throttle counted successes | locked out after 10 attempts, then refused **the correct password** with "Too many requests" | counted on failures only, per email+IP; a correct password is never refused, and success clears the count |
> | Missing account answered ~1ms vs ~180ms | a reliable oracle for which emails are registered | equalised with a dummy verify; both halves share one error message |
>
> **A bug introduced and caught during the fix**, worth recording: re-reading the row after a
> lost race fixed the 500, but *returning* it handed the loser a valid session for the winner's
> account — two people racing the same address would both be signed in, one without ever
> knowing the password. Success is now reported only when the row that exists is the one this
> request inserted. `test_a_losing_signup_is_not_handed_the_winners_account` covers it.
>
> Also added: a "the server may be waking up" hint after 4s. That is a **plaster over the
> Render free plan**, which sleeps after 15 minutes and takes ~60s to wake — the honest fix is
> a plan that does not sleep, and it is the single biggest remaining cause of "sometimes very
> slow".
>
> Browser-verified: sign-up 1.12s, sign-in with different capitalisation 0.36s, duplicate
> sign-up shows a readable error, and a correct password after four wrong ones is still accepted.
>
> Verified: **212 backend tests** (17 new), typecheck clean, 0 lint errors.
>
> **Still open:**
> - Nothing blocking. See `ACTION-REQUIRED.md` for the items that need Vishal's accounts.
>
> **Needs Vishal:** see `ACTION-REQUIRED.md` — rotate the Neon password, point `DATABASE_URL`
> at a dev branch, and verify live AI output on a machine with network access.

---

## 🔴 1. Creators cannot open their Profile or Analytics by URL

**The worst bug found.** `(app)/layout.tsx` role-guards on path prefix:

```ts
if (data.role === "INFLUENCER" && !location.pathname.startsWith("/dashboard/influencer"))
  router.replace("/dashboard/influencer")
```

`/dashboard/profile` and `/dashboard/analytics/influencer` do not start with `/dashboard/influencer`,
so they are bounced. Measured:

| Action | Result |
|---|---|
| Direct nav `/dashboard/profile` | → **kicked to `/dashboard/influencer`** |
| Direct nav `/dashboard/analytics/influencer` | → **kicked to `/dashboard/influencer`** |
| Direct nav `/dashboard/analytics/brand` (as brand) | → **kicked to `/dashboard/brand`** |
| Clicking "Dashboard" in the navbar | ✅ works (client-side nav doesn't re-run the effect) |

So it *appears* to work while clicking around, but **refresh the page, open a link in a new tab, or
bookmark anything and you are thrown back to the studio.** The profile page is where a creator
enters their Instagram handle — the single most important form in the product.

**Fix:** replace the prefix check with an explicit allowlist of shared routes (`/dashboard/profile`,
`/dashboard/brand-profile`, `/dashboard/analytics/*`), and use `usePathname()` so it re-evaluates on
navigation instead of reading `location` once at mount.

---

## 🔴 2. Creators are shown compensation figures no brand ever agreed to

Verified in the rendered card:

> **COMPENSATION** — Rs 25,000 - 40,000 per deliverable set
> **TIMELINE** — Content due within 3 weeks of accepting
> **DELIVERABLES** — 1x Instagram Reel (30-45s), 2x Story frames, Usage rights for 30 days

A brand only supplies a budget *band* ("Low/Mid/High"). Everything above is invented by the model
and rendered as fact. This is the feature creators will judge you on, and acting on an invented
number is how you lose them — or get a misrepresentation claim.

**Fix now:** show the brand's actual budget band, and label anything AI-derived
("Indicative — based on similar campaigns"). **Fix properly:** a real `Campaign` entity where the
brand states budget, deliverables and timeline, and the AI matches rather than invents.

---

## 🔴 3. Both sides are dead ends

Measured directly on the rendered cards:

- **Opportunity card: 0 buttons, 0 links.** A creator reads a full offer and can do nothing.
- **Discovery result card: 0 buttons, 0 links.** A brand ranks creators and cannot contact one.

Everything up to the moment of value works. The moment of value does not exist.

**Smallest thing that closes it:** an "I'm interested" button on the deal card, and a list of
interested creators for the brand. One table, two endpoints, two buttons.

---

## 🔴 4. Discovery ignores the niche — a Fitness campaign returned Food and Tech creators

Ran a **Fitness / Instagram / Mumbai** campaign. The API returned:

| Creator | Actual niche | Fit returned |
|---|---|---|
| Meera Nair | **Food** | **High** |
| Rohan Iyer | **Tech** | **High** |
| Diya Kapoor | **Beauty** | Medium |
| Aarav Mehta | **Fitness** | Low |

The SQL pre-filter narrows by *platform* only. `CreatorProfile.category` — which is exactly the
niche field the brand picked — is never used. (The live model would rank more sensibly than the
stub, but it is still being handed a mostly irrelevant candidate set, and the actual Fitness creator
can be crowded out.)

**Fix:** filter or heavily boost on `category == niche` in the query, before the AI sees anything.
Small change in `discover_creators`, large quality gain.

---

## 🟠 5. Discovery results are not actionable

The API returns exactly six fields per creator: `creator_id`, `creator_name`, `fit_level`,
`score_reasoning`, `risks`, `recommended_campaign_type`.

Verified absent from the brand's screen: **follower counts, engagement rate, social handles,
category, location, profile picture.** All of it exists in the database and was sent *to* the model
— it just is not returned. The card falls back to rendering `Creator 7` and the raw database id.

**Fix:** enrich the response server-side from the database (not from the model output).

---

## 🟠 6. A new creator hits a dead end 7 seconds in

Signed up fresh → landed on Creator Studio → clicked **Analyze Profile** → waited **7.1s** → got:

> Please complete your creator profile first

No link to the profile page. And per §1, typing the URL bounces you back. A new user is genuinely
stuck unless they find the avatar dropdown.

**Fix:** post-signup onboarding wizard; gate the studio cards on profile completeness with
"Complete your profile to unlock" instead of a 7-second wait for an error.

---

## 🟠 7. The navbar is white on every dark page

Visible in every screenshot: the header uses theme-aware `bg-background` (white in light mode, the
default) while the studios hard-code `bg-[#06070C]`. There is also a **white gutter** around the
dark panel, because `(app)/layout.tsx` applies `p-6` around a `min-h-screen` dark child.

This is not a theme-toggle edge case — it is what **every user sees by default**. It reads as a
broken stylesheet.

**Fix:** move the dark surface to the layout, remove the padding around full-bleed pages, and make
the navbar match. Then either fix light mode properly or remove the toggle.

---

## 🟠 8. Emoji icons render as empty boxes

Verified visually: on the Discover form, the emoji in "💰 Low / Mid / High", "📢 Awareness",
"📸 Instagram" and "🔍 Find Creators" rendered as **tofu boxes (□)** because the system had no emoji
font. macOS and Windows will render them, but Linux users and some Android browsers will see boxes —
and emoji can't be styled, sized or animated.

`lucide-react` is already installed and already used beautifully in the admin console. Swapping the
studios over is mechanical and is the highest visual-credibility-per-hour change available.

---

## 🟠 9. `GET /users/me` fired **19 times** in one creator journey

Every dashboard page calls `getCurrentUser()` independently, on top of the layout's own call. Each
one is a full round-trip that gates rendering — and `(app)/layout.tsx` returns `null` until it
resolves, so **every navigation shows a blank white screen first.**

**Fix:** fetch the user once in a context/provider (or SWR), and render a skeleton instead of `null`.

---

## Performance — measured

Stubbed AI latency was 1.6s per model call, so add roughly 2–5s per call for live Gemini.

| Action | Measured | Verdict |
|---|---|---|
| `/health` | 15ms | ✅ |
| Login (API) | 245ms | ✅ (bcrypt — correct) |
| Login (full page transition) | 3.5s | 🟠 mostly client-side redirect chain, not the API |
| Growth Analyzer | 1.8s stubbed → **~4–8s live** | ⚠️ genuine, single model call |
| Brand Deals, **2 brands** | 1.85s stubbed | ⚠️ scales at 1 call per brand |
| Discover | 1.65s stubbed → **~5–15s live** | ⚠️ genuine, one large prompt |
| Analytics page | 5.0s | 🔴 mostly the redirect bug + duplicate `/users/me` |
| Mobile 390×844 | **0px horizontal overflow** on all pages | ✅ responsive is genuinely fine |

**Brand Deals is the one that degrades as you grow** — 12 brands is 3 concurrency waves,
roughly 10–20s live. Fix by streaming results as each completes (first card in ~3s, same total) and
pre-filtering brands by niche before calling the model.

---

## Smaller verified issues

| Item | Detail |
|---|---|
| 422 validation errors render badly | FastAPI returns `detail` as an **array** for validation errors; `lib/axios.ts` passes it straight to `ApiError` as the message. Users see an object, not a sentence. |
| `.test` emails rejected | `EmailStr` blocks reserved TLDs — fine, but the resulting 422 is unreadable (above) |
| Duplicate niche input | Discover has both a chip selector *and* a free-text box that mirrors it |
| Google sign-in fails silently offline | GSI script blocked → `ERR_EMPTY_RESPONSE` in console, button just doesn't work |
| `saved_at` uses `server_default=func.now()` | Renders as `now()` — **not portable**; the migration-built SQLite schema throws `unknown function: now()` on insert. Production (Postgres) is unaffected, but it means the CI schema check (table names only) never caught a real divergence between the migration and `create_all`. Worth fixing both. |
| Two of three cards on each studio are "Coming Soon" | First impression is a mostly-unavailable product |
| Navbar has no real navigation | Logo + "Dashboard" + theme + avatar. Profile is only reachable via the avatar dropdown |

---

## What's genuinely good

Worth saying, because it sets the bar: **the admin console is a properly built product.** Real
table, lucide icons, role badges, status pills, search, filter tabs, pagination, confirmation modals
before destructive deletes. Profile completeness is computed and shown correctly.

The creator and brand studios should look like that. They currently don't.

Mobile is also fine — zero horizontal overflow at 390px across landing, studio and analytics.

---

## Recommended order

**Fix first — these are bugs, not opinions**
1. The routing guard (§1) — creators literally can't reach Profile on refresh
2. Niche filtering in discovery (§4) — matching is the product
3. Navbar/background mismatch and the white gutter (§7)
4. Duplicate `/users/me` + blank-screen-on-navigation (§9)
5. Validation error rendering (§Smaller)

**Then — makes it a marketplace**
6. "I'm interested" + interested-creators list (§3)
7. Stop presenting invented commercial terms as fact (§2)
8. Enrich discovery results with real creator data (§5)
9. Onboarding wizard (§6)

**Then — makes it feel professional**
10. Emoji → lucide across both studios (§8)
11. Stream Brand Deals; pre-filter brands by niche
12. Skeletons instead of blank screens; toasts instead of `alert()`

§1 and §4 are the ones I'd do today — one makes the app usable, the other makes the matching mean
something. §2 and §3 are what turn it from a demo into a business.
