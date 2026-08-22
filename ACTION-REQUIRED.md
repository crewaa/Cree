# ACTION REQUIRED — things only Vishal can do

> Running list of anything credential-, config- or infrastructure-related that Claude
> changed, moved, or could not do. **Nothing here is lost** — this file exists so that
> if you forget, you can pick it up later without hunting through chat history.
>
> **This file must never contain an actual secret value.** Names and locations only.
> Last updated: 2026-08-13.

---

## ⏰ BEFORE PUSHING TO GITHUB — read this first

Vishal asked to be reminded of these at push time. Claude: surface this list *before* running
any `git push`, not after.

**1. Set the Sentry DSNs on both hosts.** Local `.env` files are gitignored, so deploying does
not carry them. Until this is done, production runs with error tracking silently off.

| Host | What runs there | Variable | Value |
|---|---|---|---|
| **Vercel** | Next.js frontend | `NEXT_PUBLIC_SENTRY_DSN` | the `crewaa-frontend` DSN |
| **Render** | FastAPI backend | `SENTRY_DSN` | the `crewaa-backend` DSN |

Add `SENTRY_ENVIRONMENT=production` on both as well, so real user errors are not mixed in with
local debugging.

Two ways this silently fails to take effect:

* **Vercel** inlines `NEXT_PUBLIC_*` at *build* time. Adding the variable does nothing to the
  currently deployed site — you must **redeploy** afterwards.
* **Render** asks *"Save only"* or *"Save and deploy"* when you edit a variable. **Save only**
  leaves the running service on its old values until the next deploy, so the dashboard shows
  the DSN while the app never sees it. Choose *Save and deploy*.

**2. One migration in this batch cannot be tested before it runs on Neon.**
`f7a2c4e91b35` converts `creator_profiles.ai_summary` and `.cached_brand_deals` from TEXT to
JSONB. The test suite runs on SQLite, where the migration is a deliberate no-op, and no
PostgreSQL was available to rehearse it against — so the PostgreSQL branch is verified by
inspection and by unit tests of its Python half, not by execution.

It is written to be as safe as that allows: rows holding invalid JSON are set to NULL *before*
the cast, so a single bad row cannot abort the deploy, and these are caches — a cleared value
costs the user one regeneration. The exact SQL it will run is:

```sql
ALTER TABLE creator_profiles ALTER COLUMN ai_summary        TYPE JSONB USING ai_summary::jsonb;
ALTER TABLE creator_profiles ALTER COLUMN cached_brand_deals TYPE JSONB USING cached_brand_deals::jsonb;
```

Before deploying, run `alembic upgrade head` against a **Neon branch** (a throwaway copy of
production) rather than production itself. That is the rehearsal this repository could not do.

**3. The Neon password is still unrotated** and still in git history — see §1 and §4 below.
Pushing does not make that worse, but it does not fix it either.

**4. Decide whether the repo is public.** If it is, §3 (purging the credential from history)
stops being housekeeping and becomes urgent.

---

## 🔴 1. Rotate the Neon database password — STILL OPEN

**What happened:** `backend/alembic.ini` contained a complete Neon connection string,
password and all, committed to git and present in the full history.

**What Claude changed:** the value in `alembic.ini` is now blank. `app/migrations/env.py`
reads `DATABASE_URL` from the environment instead and converts the async driver for
Alembic. **Nothing was deleted from your `.env`** — the real connection string is still
there and everything still works.

**Why it is still open:** removing it from the file does not invalidate it. The old
password remains valid and remains in git history, so anyone who ever cloned the repo
still has working production credentials.

**Steps:**
1. <https://console.neon.tech> → Crewaa project.
2. **Roles** (or Branches → your branch → Roles) → `neondb_owner` → **Reset password**.
   Copy it — shown once.
3. Update `backend/.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://neondb_owner:<NEW_PASSWORD>@<host>/neondb
   ```
   Keep `+asyncpg`; Alembic converts it automatically.
4. Update the same variable wherever the backend is deployed, and redeploy.
5. Neon → **Monitoring → Connections**: look for unfamiliar activity during the
   exposure window.
6. Confirm: `curl localhost:8000/health` → `{"status":"ok","database":"ok"}`.

---

## 🟠 2. `DATABASE_URL` in `backend/.env` points at PRODUCTION

Your `.env` `DATABASE_URL` is the live Neon database. Anyone who runs the repo locally
is developing directly against production data — a stray `alembic upgrade`, a test
script, or a seed run would hit real users.

Claude never touched it: every local run during this work used a separate SQLite file
and production was never contacted.

**Suggested:** create a Neon **dev branch** and point local `.env` at that. Keep the
production URL only in the deployment environment.

---

## 🟠 3. Purge the leaked credential from git history

Only worth doing *after* rotation (step 1), and only if the repo is or may become public.

```bash
# Rewrites history — everyone with a clone must re-clone afterwards.
git filter-repo --path backend/alembic.ini --invert-paths
```

Decide based on whether the repo is private and who has had access.

---

## 🟡 4. Unused secrets in `backend/.env`

Present in the file but not read by `app/core/config.py`:

| Variable | Status |
|---|---|
| `GOOGLE_CLIENT_SECRET` | **Not used.** The backend verifies Google ID tokens against `GOOGLE_CLIENT_ID` only; no OAuth code exchange happens. A client secret sitting unused is a liability — consider removing it. |
| `SCRAPE_TTL_DAYS` | Not read by config; ignored. |
| `REDIS_URL` | Read by config but nothing uses it (the Redis cache was dead code and was deleted). |
| `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | These are **frontend** variables. They belong in `frontend/.env.local`; the backend ignores them. |

`REFRESH_TOKEN_EXPIRE_DAYS` is read but unused — refresh tokens are configured and never
implemented.

---

## 🟡 5b. Record the first real prompt-eval baseline

`backend/evals/` measures whether the AI matching is any *good* — the thing the normal tests
cannot see. It runs in CI in replay mode, but replay scores frozen responses and cannot detect
the model getting worse.

Worse, the shipped fixtures are **hand-written, not captured from Gemini**: this environment had
no network route to Google. So the numbers a replay run prints are about the pipeline, not the
model.

One command from your Mac fixes that permanently:

```bash
cd backend && source .venv/bin/activate
python -m evals.runner --live --record
```

That calls the real Gemini once per case (8 calls), overwrites `evals/recorded.json` with real
output, and writes the first `evals/baseline.json`. From then on:

```bash
python -m evals.runner --live --repeat 3   # before and after any prompt change
```

reports the movement against that baseline. Read `backend/evals/README.md` first — it explains
what a violation is versus a miss, and why the suite judges on the worst of N runs.

---

## 🟡 5. Verification that needs your machine

The sandbox has no outbound network to Google or Apify, so these were never exercised
against the live services:

- Real Gemini output quality and timings (estimates: ~4–8s Growth Analyzer, ~5–15s Discover)
- A real Instagram scrape end to end via Apify
- Anything against real PostgreSQL — all testing used SQLite

To verify, run locally with your real keys:
```bash
cd backend && ./scripts/setup-dev.sh     # rebuilds .venv for macOS
source .venv/bin/activate && uvicorn app.main:app --reload
# separate terminal
cd frontend && pnpm dev
```
Then say so and Claude can drive Chrome against `localhost:3000`.

---

## 🟡 6. Sentry — configured locally, needs deploying

Both projects exist and both DSNs are installed **locally**:

| File | Variable | Sentry project | Status |
|---|---|---|---|
| `backend/.env` | `SENTRY_DSN` | `crewaa-backend` | ✅ set |
| `frontend/.env.local` | `NEXT_PUBLIC_SENTRY_DSN` | `crewaa-frontend` | ✅ set (new file, gitignored) |

Backend boot now logs `Error tracking enabled`. Both files are gitignored.

### Still to do — three things

**a) Confirm events actually arrive.** Nothing is proven until an event lands; the sandbox
has no network to Sentry, so this has to run on your Mac:

```bash
cd backend && source .venv/bin/activate && python scripts/verify-sentry.py
```

It sends one error with a fake password and a fake API key in local scope. In Sentry →
`crewaa-backend` → Issues you should see **"Crewaa test error - safe to ignore"**, and the
strings `canary-PASSWORD` / `canary-APIKEY` should appear **nowhere** on it. That single check
proves the DSN, the network path, and that frame locals are not leaking. Delete the issue after.

For the frontend: `cd frontend && pnpm dev`, open any page, and in the browser console run
`myUndefinedFunction()`. An issue should appear in `crewaa-frontend`.

**b) Set the variables on your hosts.** Local config does nothing for deployed users.

- **Vercel** → Project Settings → Environment Variables → add `NEXT_PUBLIC_SENTRY_DSN`
  (the frontend DSN) for Production and Preview, then redeploy. It is inlined at *build*
  time, so an existing deployment will not pick it up without a rebuild.
- **Backend host** → add `SENTRY_DSN` (the backend DSN) wherever the API runs. That host is
  still recorded as unknown in these docs — tell Claude where it is and this section can be
  made specific.

Also set `SENTRY_ENVIRONMENT=production` on both, so your own local debugging does not land in
the same bucket as real user errors.

**c) Do not run the Sentry wizard.** Sentry's setup page suggests
`npx @sentry/wizard@latest -i nextjs`. **Don't.** The config is already written by hand, and
the wizard would overwrite it — including the privacy settings below.

### What is deliberately off, and should stay off

- **Frame-local variables.** Sentry sends every stack frame's locals by default. Yours hold the
  Neon password, the JWT signing key and every API key. Disabled, with a test asserting a real
  crash leaks neither.
- **Session replay.** It records the user's screen — a creator's private analytics, a brand's
  budget.
- **PII.** No emails, no IP addresses.
- **Tracing** (`SENTRY_TRACES_SAMPLE_RATE=0.0`). Billed separately from errors.

### Two things to watch

- **Free tier is 5,000 errors/month, 1 user, 30-day history.** Every existing
  `logger.error(...)` in the backend now becomes a Sentry issue, so one broken loop in
  production could burn the quota. Worth checking the usage page in the first week.
- **`pytest` will not touch the real project.** `conftest.py` forces `SENTRY_DSN=""`, because
  the test suite raises errors on purpose and would otherwise file dozens of fake issues
  against production. `tests/test_no_live_sentry_in_tests.py` fails the build if that override
  is ever removed.

---

## Things Claude changed that are NOT losses

For peace of mind — these look like removals but nothing was destroyed:

| Change | Reality |
|---|---|
| `alembic.ini` connection string blanked | Same URL still in `backend/.env`; Alembic reads it from there |
| `backend/.venv` | Built inside a Linux sandbox on Python 3.10 — **will not work on macOS**. Run `./scripts/setup-dev.sh` to rebuild. Gitignored. |
| `fix_alembic.py`, `test_db.py`, `validate_setup.py` deleted | Throwaway scripts. `fix_alembic.py` force-stamped `alembic_version` — a workaround for the destructive migration, which is now properly fixed. |
| `redis` dependency removed | The cache module was imported nowhere. |
| Celery worker / cron scraper deleted | Celery was never a dependency; the cron script queried a field that does not exist. Neither could ever have run. |
| Theme toggle removed from the navbar | Light mode was half-implemented and visibly broken. `ThemeProvider` is still mounted, so it can be restored once light mode is actually built. |
