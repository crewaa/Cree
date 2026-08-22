# Crewaa — Architecture

> Verified against the code at commit `5e58465`.

---

## 1. Topology

```
                    Browser
                       │
                       │  JWT in localStorage, sent via axios interceptor
                       ▼
          ┌────────────────────────────┐
          │  Next.js 16 (App Router)   │   Vercel  [V: CORS allowlist]
          │  frontend/                 │
          │  100% client components    │
          │  for anything authenticated│
          └────────────┬───────────────┘
                       │  NEXT_PUBLIC_API_URL  (direct browser → API; no BFF)
                       ▼
          ┌────────────────────────────┐
          │  FastAPI modular monolith  │   Render (no config in repo)
          │  backend/app/main.py       │
          │  7 routers, no middleware  │
          │  except CORS               │
          └───┬─────────┬─────────┬────┘
              │         │         │
              ▼         ▼         ▼
    ┌─────────────┐ ┌────────┐ ┌──────────────────┐
    │ PostgreSQL  │ │ Gemini │ │ Apify (Instagram)│
    │ Neon        │ │ 2.5    │ │ YouTube Data API │
    │ us-east-1   │ │ flash  │ │                  │
    └─────────────┘ └────────┘ └──────────────────┘
```

**[V] There is no gateway, no CDN in front of the API, no queue, no cache in the request path, no object storage, and no background worker process.** Redis and Celery exist as files but are wired to nothing (see `CLAUDE.md` → dead code).

---

## 2. Backend structure — modular monolith

`app/main.py` is 35 lines: create the app, add CORS, include 7 routers. There is no startup event, no shutdown hook, no exception handler, no request-ID middleware, and no logging configuration.

Each module under `app/modules/` roughly follows `router → service → models`, but consistency varies:

| Module | Router | Service | Models | Schemas | Notes |
|---|---|---|---|---|---|
| `auth` | ✅ | ✅ | uses `users` | ✅ | cleanest module |
| `users` | ✅ | partial | ✅ | ✅ | most CRUD is inline in the router |
| `admin` | ✅ | ✅ | uses `users` | ✅ | consistent; only module with a real auth dependency |
| `ai` | ✅ | `ai_service.py` | — | ✅ | the router does payload building **and** persistence |
| `instagram` | ✅ | ✅ | ✅ | ❌ | deepest nesting: `routes/`, `services/`, `scrapper/`, `workers/`, `cron/`, `models/` |
| `youtube` | ✅ | ✅ | ✅ | ❌ | flat layout — inconsistent with `instagram` |
| `health` | ✅ | — | — | — | `GET /health` |
| `roles` | — | empty | empty | — | stub |

**Convention drift to be aware of:** `instagram` uses a nested package layout while `youtube` is flat, and `app/models/` exists purely as re-export shims (`app/models/user.py` is a single import line) so that `app/migrations/env.py`'s `from app.models import *` can see every mapper. Do not delete those shims — Alembic autogenerate depends on them.

---

## 3. Database access

`app/core/database.py` creates one async engine at import time with `connect_args={"ssl": "require"}` and an `async_sessionmaker`.

Sessions are obtained two ways **[V]**:

1. `Depends(get_db)` in request handlers — from `app/common/dependencies.py` (and a **duplicate copy** of `get_db` defined locally in `app/modules/auth/router.py`).
2. `async with AsyncSessionLocal()` inside background tasks — required because a request-scoped session dies when the response is returned.

**Bug of note [V]:** `youtube/routes.py` does `background_tasks.add_task(scrape_and_store_youtube, user_id, db)` — passing the **request-scoped session** into a background task. Instagram's equivalent correctly opens its own session. The YouTube path is racing a session that FastAPI is closing. Instagram gets it right, YouTube does not.

No connection-pool tuning, no `pool_pre_ping`, no statement timeout is configured. On Neon's serverless Postgres, idle connection drops are a realistic failure mode **[I]**.

---

## 4. Request flows

### 4.1 Email/password login
```
POST /auth/login {email, password}
  → authenticate_user(): SELECT user by email → bcrypt verify
  → create_access_token({sub: user.id, role}, ACCESS_TOKEN_EXPIRE_MINUTES)
  → {access_token, token_type, role}
Frontend: localStorage.setItem("access_token", ...) → route by role
```

### 4.2 Google Sign-In (three cases)
```
Browser gets a Google ID token via @react-oauth/google
POST /auth/google {id_token, role?}
  → verify_google_token(): GET oauth2.googleapis.com/tokeninfo, assert aud == GOOGLE_CLIENT_ID
  → CASE 1  user exists WITH password  → return access_token (straight login)
  → CASE 2  user exists WITHOUT password → return 10-min setup_token, needs_password: true
  → CASE 3  new user → create with hashed_password=NULL → return setup_token
Frontend: if needs_password → /set-password?token=...&email=...
POST /auth/set-password {setup_token, password} → sets password, returns real access_token
```
The setup token is a separate JWT carrying `purpose: "set_password"`, signed with the **same** `JWT_SECRET_KEY` as access tokens. `decode_setup_token()` does check `purpose`, but `get_current_user()` does **not** check that an incoming token *lacks* that purpose — see `docs/07-risks-and-gaps.md` §4.

### 4.3 Authenticated request
```
axios request interceptor attaches Authorization: Bearer <localStorage token>
  → get_current_user(): jwt.decode → payload["sub"] → SELECT User by id
  → handler does its own `if current_user.role != "X": raise 403`
```
Note the role is present *in* the JWT but the code always re-reads the user from the DB and uses `user.role`, not the claim — which is the safer choice **[V]**.

### 4.4 Instagram scrape
```
POST /instagram/scrape/{user_id}          ← NO AUTH [V]
  → BackgroundTasks.add_task(scrape_and_store, user_id)   → returns 200 immediately
  → task opens its own session
  → reads creator_profiles.instagram_username
  → Apify actor "apify/instagram-profile-scraper" (blocking .call(), resultsLimit 12)
  → maps fields, INSERTS a new InstagramProfile + up to 15 InstagramPost rows
    (append-only: every scrape adds a new snapshot, keyed by scraped_at)
GET /instagram/analytics/{user_id}        ← NO AUTH [V]
  → latest profile by scraped_at, then posts matching that exact scraped_at
```
The Apify call is **synchronous, blocking I/O executed in an async background task** — it blocks the event loop for the duration of the actor run (tens of seconds) **[V]**. It should be wrapped in `run_in_threadpool`.

### 4.5 YouTube scrape
```
POST /youtube/scrape/{user_id}            ← NO AUTH [V]
  → background task (with the leaked session, see §3)
  → reads creator_profiles.youtube_username
  → YouTube Data API: search → channels → playlistItems → videos  (4 calls, ~100 quota units)
  → UPSERT channel by channel_id; DELETE all old videos; INSERT up to 15 new
```
Different persistence semantics from Instagram: YouTube replaces, Instagram appends. That asymmetry means historical YouTube trend data is destroyed on every scrape.

`is_verified` for a channel is derived by checking whether the string `"verified"` appears in the channel description **[V]** — this is not a real verification signal.

### 4.6 AI discovery (brand)
```
POST /ai/discover-creators {niche, budget_range, campaign_goal, ...}
  → 403 unless role == BRAND
  → build brand payload (enriched from brand_profiles if present)
  → SELECT * FROM creator_profiles          ← every creator, unfiltered
  → for each: N+1 queries (IG profile, IG posts, YT channel, YT videos)
  → ONE Gemini call with all of it in the prompt
  → regex-extract JSON from the response
  → upsert each ranked creator into saved_creators
```

### 4.7 AI brand deals (creator)
```
POST /ai/brand-deals
  → 403 unless role == INFLUENCER
  → build creator payload
  → SELECT * FROM brand_profiles
  → for each brand: one Gemini call + asyncio.sleep(2)
  → cache the whole list as JSON in creator_profiles.cached_brand_deals
GET /ai/brand-deals → returns the cached JSON, or null
```

---

## 5. Concurrency and performance characteristics

- **N+1 queries** in `_build_creator_payload`: 4 queries per creator, called in a loop over all creators.
- **No pagination** on the creator or brand fan-out.
- **No timeouts** on Gemini calls; `httpx` YouTube calls use `timeout=30.0` **[V]**.
- **No retries** anywhere — deliberate for Gemini ("no retries to conserve quota" **[V]**), accidental elsewhere.
- **Blocking calls in async context**: Apify SDK (`instagram`), and `genai.generate_content` (all AI endpoints) are synchronous and block the event loop.
- **Background tasks are in-process** — a deploy or crash loses any in-flight scrape silently, with no record that it was ever queued.

---

## 6. What is not here

The backend runs on **Render** and the frontend on **Vercel** (confirmed by Vishal,
2026-08-13). Neither is visible from the repository: there is a `backend/Dockerfile` but no
`render.yaml`, no Procfile and no Vercel config, so the service name, plan, region, process
manager and public API URL are still **[?]** — read them from the Render dashboard, not from
here.

Two Render behaviours that have bitten this kind of setup:

* Editing an environment variable offers **"Save only"** or **"Save and deploy"**. *Save only*
  leaves the running service on its old values until the next deploy — so a variable can look
  set in the dashboard and do nothing. This applies to `SENTRY_DSN`.
* A **Free** web service spins down after 15 minutes without traffic and takes about a minute
  to come back. For Crewaa that means a brand landing on the site cold waits ~60s for the
  first API call, which reads as broken. If the service is on the free plan this matters more
  than any feature in this document.
**[?]** No observability: no APM, no error tracking, no metrics, no structured logs, no health checks beyond `GET /health` returning a static `{"status": "ok"}` that does not touch the database.
**[?]** No rate limiting, no request size limits, no idempotency keys.
