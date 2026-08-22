# Hardening Pass — 2026-08-10

> Two sessions of work closing every finding in `docs/07-risks-and-gaps.md` that could
> leak data, cost money, corrupt records, or fail silently. No new product features.
> All changes are local and unpushed.

**Verification, run end to end:**

| Check | Result |
|---|---|
| Backend test suite | **86 passed** |
| Migrations from an empty database | 9 tables, **zero drift** vs the models |
| Migrations re-run (idempotency) | clean no-op |
| Route auth audit | **30 routes, 0 unprotected** |
| Frontend `tsc --noEmit` | clean |
| Frontend `eslint` | **0 errors** (was 30) |
| Frontend `next build` | compiles, 25 routes |
| Secret scan | clean, and verified it still catches a real credential |

The only item deliberately left open is rotating the Neon password, at your request.

---

## Session 1 — security and correctness

### 1. Removed the committed database credential
`backend/alembic.ini` · `backend/app/migrations/env.py`

`sqlalchemy.url` held a full Neon connection string including the password. It is now empty;
`env.py` builds the URL from `DATABASE_URL` at runtime and swaps the async driver for a sync one.
Alembic fails with a clear message if the variable is unset.

> **Still required: rotate the password in the Neon console.** The old one remains valid and is
> in git history. Steps at the bottom of this document.

### 2. Closed every unauthenticated endpoint
New `require_self_or_admin` guard resolves the `{user_id}` path parameter and allows the request
only if the caller is that user or an admin. Applied to all Instagram/YouTube scrape and analytics
routes.

`GET` and `PUT /users/creator-profile/{user_id}` were **deleted**. The PUT let an anonymous caller
rewrite any creator's profile — including the Instagram handle that redirects their scraping.
Neither had a live consumer: the only caller was reachable solely through `creator-dashboard.tsx`,
which is not routed anywhere.

### 3. Hardened the token boundary
Setup tokens (issued for 10 minutes during Google sign-up) are signed with the same secret as
access tokens. `get_current_user()` now rejects any token carrying `purpose: "set_password"`, and
access tokens carry `type: "access"`. Previously this was safe only *by accident* — the setup token
happens to lack a `sub` claim.

Also: `is_active` is now enforced at login, set-password and on every request; `set_password`
refuses to overwrite an existing password; minimum password length of 8; signup whitelists
BRAND/INFLUENCER rather than only blocking ADMIN.

The `type` claim is additive, so **existing sessions are not invalidated**.

### 4. Fixed the YouTube background task
The route passed the request-scoped session into a `BackgroundTask`, which FastAPI closes when the
response returns. It now opens its own session, matching the Instagram scraper.

Also fixed the cross-account upsert: the channel lookup matched on `channel_id` alone, so a second
user claiming the same channel overwrote the first user's row. Now scoped to `(user_id, channel_id)`,
with an explicit refusal when a channel is already claimed.

### 5. Stopped trusting LLM output as a foreign key
`discover_creators` used Gemini's `creator_id` directly as an FK. A hallucinated id either aborted
the whole commit (losing every result) or persisted a false match. Ids are now validated against the
set actually sent. The AI endpoints also no longer echo raw upstream exception text to clients.

### 6. Real logging and a real health check
Configured loguru (a declared dependency that was never imported) with `diagnose=False`, so local
variables — tokens, keys, payloads — can never appear in a traceback. Every `print()` in live code
paths replaced. `GET /health` now runs `SELECT 1` and returns 503 when the database is unreachable;
it previously returned a static "ok" that would report healthy during a total outage.

### 7. Frontend correctness
The wrong-id scrape bug is gone: `profile/page.tsx` posted to `/instagram/scrape/${savedProfile.id}`
where that id is `creator_profiles.id`, not `users.id`. Both calls were deleted — the backend
already queues the scrape correctly — and the backend now also queues a YouTube scrape, which it
previously did only for Instagram.

`ApiError` replaces the bare `Error` thrown by the axios interceptor, preserving `status` and
`detail`; a 401 clears the dead token. The login page gained the missing error handling (a failed
login previously threw into an unhandled promise rejection and appeared to do nothing), the
`blindnessClassName` typo fix, proper input attributes, and the missing ADMIN redirect.

---

## Session 2 — everything else

### 8. Repaired the destructive migration chain
`dd173ce633c3` — titled "Add caching columns" while actually dropping `saved_creators` — is now a
documented no-op. New revision `b7e4c1a90f22` recreates the table **idempotently**: it inspects the
live schema and only creates what is absent, so it is safe whether production still has the table
or lost it. It also adds the `(brand_id, creator_id)` unique constraint the model always implied,
collapsing any duplicates first.

Verified three ways: a database built from zero matches the models exactly; the production repair
path deduplicates and applies the constraint correctly; and a second `upgrade head` is a clean no-op.

> This means the migration item no longer blocks you. Running `alembic upgrade head` is now safe.
> Sending me the production `alembic_version` would still be worth doing as a sanity check.

### 9. Took blocking calls off the event loop
The Apify SDK is synchronous (Gemini has since moved to the async `google-genai` client). Called directly from async handlers they
stalled every other request on the worker for the whole actor run or model call. Both now go through
`run_in_threadpool`. Gemini also gained a request timeout and a configurable model id.

### 10. Made the AI endpoints scale
`discover-creators` previously ran four queries **per creator** and serialised every creator in the
database into one prompt. It now filters candidates in SQL by platform, prefers the target location,
caps the set, and builds all payloads in four queries total.

`brand-deals` looped serially with a hard-coded `asyncio.sleep(2)` between calls. It now uses a
bounded semaphore, caps the fan-out, and reports partial failures instead of hiding them.

All limits are configurable: `AI_MAX_CREATORS_PER_PROMPT`, `AI_MAX_BRANDS_PER_RUN`,
`AI_MAX_CONCURRENT_CALLS`, `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS`.

### 11. Prompt injection and brand anonymity
Scraped Instagram bios and captions are attacker-controlled and went raw into every prompt. They are
now fenced in labelled data blocks, preceded by an instruction to treat the contents as data.

More importantly, **brand anonymity is now enforced rather than requested**. The Brand Deals feature
promises creators cannot identify the brand, and that rested entirely on one instruction line with
no validation. Output is now scrubbed of brand name, website and contact details, and a leak is
logged as a prompt-safety failure. There are tests proving a deliberately leaking model response
gets cleaned.

`extract_json` was rewritten. The old greedy `\{.*\}` regex spanned the first brace to the *last*
brace anywhere in the response, so trailing prose or a brace inside a string produced invalid JSON.
It now walks the string tracking brace depth and string state.

### 12. Rate limiting
New `app/common/rate_limit.py`. Credential endpoints are throttled by IP (login was an unbounded
password-guessing oracle); scrape and AI endpoints are throttled per **user account**, which is the
right key since those spend real money and an attacker can rotate IPs but not accounts.

The counter is per-process — documented in the module — so multiple workers multiply the effective
limit. Swapping in Redis later needs no signature change.

### 13. Scrape failures are visible
New `scrape_jobs` table plus `GET /instagram|youtube/scrape-status/{user_id}`. Previously a failed
scrape logged to stdout and the user stared at an empty dashboard forever with no way to tell
"running" from "failed". Both analytics components now poll job status and surface a plain-language
reason ("the account may be private, renamed, or Instagram may be rate-limiting us").

User-facing messages deliberately exclude internal detail — there is a test asserting the raw
exception text does not reach the user.

### 14. Deleted dead code
Removed the Celery worker (Celery was never a dependency), the cron script (queried a field that
does not exist), the Redis cache (imported nowhere), `youtube_extractor.py` (raised at import),
`validate_setup.py`, `fix_alembic.py`, `test_db.py`, and four empty stub files. Each was verified
unreferenced first. `redis` dropped from dependencies.

Also removed the **duplicate `get_db`** in `auth/router.py` — two session providers meant auth
routes silently bypassed anything applied to the shared dependency. The test suite caught this.

### 15. Test suite — 86 tests
`backend/tests/`, running against a real SQLite database per test with foreign keys enabled, no
network access:

| File | Covers |
|---|---|
| `test_auth_boundary.py` | setup-token rejection, forged claims, `is_active`, password rules |
| `test_authorization.py` | **route audit that fails if any endpoint loses its guard**, ownership, role guards |
| `test_ai_safety.py` | JSON extraction regressions, anonymity scrubbing, hallucinated ids |
| `test_scraping.py` | field mappers, job bookkeeping, cross-account channel claim |
| `test_rate_limit.py` | window behaviour, brute-force throttling, per-user isolation |
| `test_profile_flows.py` | profile CRUD, correct scrape queueing, cascade deletes |

### 16. CI, tooling, config
`.github/workflows/ci.yml` runs backend tests, **verifies migrations produce a schema matching the
models** (a direct guard against another `dd173ce633c3`), frontend typecheck/lint/build, and a
secret scan that would have caught the original credential leak.

Also: CORS origins from config; request-id middleware and access logging; a catch-all exception
handler returning a traceable id instead of a stack trace; admin pagination clamped (`page=0`
previously caused a database error); `backend/Dockerfile`; `backend/scripts/setup-dev.sh`; proper
`.gitignore` files.

### 17. Frontend type safety
Went from 30 lint errors to zero. Replaced every `any` with real types in a new `lib/types.ts`.

This surfaced a **live bug**: `ProfileDropdown` rendered `user.name`, but `GET /users/me` returns
only `{id, email, role}` — so the name line has been blank for every user in production. It now
falls back to the email. Two other latent type mismatches were fixed the same way. The Google
sign-in button also now uses the shared API client instead of raw axios, so it gets consistent
error handling.

---

## What is still open

| Item | Status |
|---|---|
| **Rotate the Neon password** | **Yours to do** — steps below. The code is ready. |
| Purge the credential from git history | Decide after rotation; needs coordinating with any clone holders |
| Error tracking (Sentry or similar) | Not added — needs an account and a DSN |
| Background jobs on a real queue | The AI endpoints are now bounded and fast enough; a queue is a v2 architecture decision |
| Prompt evals | Anonymity is enforced and tested, but there is still no quality regression suite for prompt changes |
| ~~`google-generativeai` is end-of-life~~ | ✅ **RESOLVED 2026-08-13** — migrated to `google-genai`, now natively async with typed errors and `response_mime_type` JSON enforcement. `extract_json` is kept as a fallback |

---

## Notes for running this locally

A virtualenv exists at `backend/.venv`, but **it was built inside a Linux sandbox on Python 3.10 and
will not work on your Mac**. Recreate it:

```bash
cd backend
./scripts/setup-dev.sh          # removes .venv, rebuilds it, writes a starter .env
source .venv/bin/activate
pytest -q                       # expect 86 passed
uvicorn app.main:app --reload
```

The script requires Python 3.11+. If your default `python3` is older:
`PYTHON=python3.12 ./scripts/setup-dev.sh`.

Frontend is unchanged in workflow: `cd frontend && pnpm install && pnpm dev`.

---

## Rotating the Neon password

1. Open <https://console.neon.tech> → the Crewaa project.
2. **Roles** (or Branches → your branch → Roles) → `neondb_owner` → **Reset password**. Copy it; it
   is shown once.
3. Update `backend/.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://neondb_owner:<NEW_PASSWORD>@<host>/neondb
   ```
   Keep `+asyncpg` — Alembic converts it automatically.
4. Update the same variable wherever the backend is deployed, and redeploy.
5. Check **Monitoring → Connections** in Neon for unfamiliar activity during the exposure window.
6. Confirm: `curl localhost:8000/health` should return
   `{"status":"ok","database":"ok"}`.

Rotation is what actually closes this — the old password stays in git history until it is purged.
