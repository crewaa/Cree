# Crewaa — API Surface

> Every endpoint registered in `backend/app/main.py`, verified at commit `5e58465`.
> Base URL comes from `NEXT_PUBLIC_API_URL` on the frontend. Local default `http://localhost:8000`.
> There is **no API versioning** and **no OpenAPI customisation** — FastAPI's auto-docs at `/docs` are live and unprotected **[V]**.

Auth column: **None** = no dependency at all · **JWT** = `get_current_user` · **JWT+role** = plus an inline role check.

---

## Auth — `/auth`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | None | Create BRAND/INFLUENCER. Rejects `role="ADMIN"`. Returns `{access_token, token_type, role}` |
| POST | `/auth/login` | None | Email+password → access token |
| POST | `/auth/google` | None | Verify Google ID token → login, or return a 10-min `setup_token` |
| POST | `/auth/set-password` | setup_token in body | Set password for a Google-created account → access token |
| POST | `/auth/logout` | None | 204. Deletes a `refresh_token` cookie **that is never set**. Effectively a no-op |

Notes:
- `/auth/signup` **[V] calls the DB twice** — it creates the user, then immediately calls `authenticate_user()` to log them in, re-running a bcrypt verify against the password it just hashed. Wasteful but correct.
- `/auth/signup` **[V] has no password strength requirement, no email verification, and no rate limit.**
- **[V] There is no refresh-token endpoint.** `REFRESH_TOKEN_EXPIRE_DAYS` is configured and unused. When the access token expires the user is silently bounced to `/login`.

---

## Users — `/users`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/users/me` | JWT | Current user `{id, email, role}` |
| POST | `/users/creator-profile` | JWT + INFLUENCER | Create profile; **fires a background Instagram scrape** if `instagram_username` present |
| GET | `/users/creator-profile` | JWT + INFLUENCER | Own profile |
| PUT | `/users/creator-profile` | JWT + INFLUENCER | Update own profile; re-triggers Instagram scrape |
| ~~GET~~ | ~~`/users/creator-profile/{user_id}`~~ | — | **REMOVED** 2026-08-10 (was unauthenticated) |
| ~~PUT~~ | ~~`/users/creator-profile/{user_id}`~~ | — | **REMOVED** 2026-08-10 (was unauthenticated; anyone could overwrite any profile) |
| POST | `/users/brand-profile` | JWT + BRAND | Create brand profile |
| GET | `/users/brand-profile` | JWT + BRAND | Own brand profile |
| PUT | `/users/brand-profile` | JWT + BRAND | Update own brand profile |
| GET | `/users/saved-creators` | JWT + BRAND | Rows from the last discovery run, joined to creator name/category/platform |

✅ **Both `{user_id}` variants were deleted in the 2026-08-10 hardening pass.** They took no authentication dependency at all; the PUT allowed an anonymous caller to rewrite any creator's name, location, category and social handles — and changing `instagram_username` also redirected that creator's scraping. Neither had a live consumer. The authenticated `/users/creator-profile` routes cover the same use case, and admins can read any creator via `GET /admin/users/{id}`.

---

## Instagram — `/instagram` ✅ secured 2026-08-10

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/instagram/scrape/{user_id}` | JWT + self-or-admin | Queue a background Apify scrape. Returns 200 immediately, always — even for a nonexistent user |
| GET | `/instagram/analytics/{user_id}` | JWT + self-or-admin | Latest profile snapshot + up to 15 posts from that snapshot |

Both routes previously took no authentication: anyone could enumerate every creator's analytics by incrementing `user_id`, and burn Apify credits by hammering the scrape endpoint. They now use `require_self_or_admin`. **There is still no rate limit and no per-user cost cap** — an authenticated user can call scrape repeatedly.

**[V] The response never reports scrape failure.** `scrape_and_store` returns error dicts that FastAPI discards (background task return values go nowhere), and errors are only `print()`ed. The client polls `/analytics` and gives up.

---

## YouTube — `/youtube` ✅ secured 2026-08-10

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/youtube/scrape/{user_id}` | JWT + self-or-admin | Background YouTube Data API scrape (now opens its own DB session) |
| GET | `/youtube/analytics/{user_id}` | JWT + self-or-admin | Latest channel + up to 15 videos |

Previously open, with the same exposure as Instagram plus a quota-exhaustion vector: each scrape costs ~100+ units against a default 10,000/day budget, so ~100 anonymous requests could exhaust the day **[I]**. The session leak into the background task is also fixed.

---

## AI — `/ai`

| Method | Path | Auth | Purpose | Gemini calls |
|---|---|---|---|---|
| GET | `/ai/creator-summary` | JWT + INFLUENCER | Cached summary, or `null` | 0 |
| POST | `/ai/creator-summary` | JWT + INFLUENCER | Generate + cache growth analysis | 1 |
| POST | `/ai/discover-creators` | JWT + BRAND | Rank creators; upsert into `saved_creators` | 1 |
| GET | `/ai/brand-deals` | JWT + INFLUENCER | Cached opportunities, or `null` | 0 |
| POST | `/ai/brand-deals` | JWT + INFLUENCER | Generate opportunities across **all** brands | **1 per brand** |
| POST | `/ai/brand-deals/stream` | JWT + INFLUENCER | Same run, NDJSON, one card per line | **1 per brand** |

Error contract **[V]**:
- `403` wrong role · `404` profile missing · `429` Gemini quota/rate limit · `500` any other AI failure.
- ✅ The `500` path no longer echoes raw upstream exception text; the detail is logged server-side and the client receives a generic message (fixed 2026-08-10).
- `POST /ai/brand-deals` **swallows per-brand failures silently** (`except Exception: print(...); continue`), so a partial result is indistinguishable from a complete one.

`POST /ai/brand-deals/stream` emits NDJSON, one JSON object per line:
`{"type":"opportunity","opportunity":{...}}` repeatedly, then `{"type":"done","total":N,
"generated_at":"..."}`. Late failures arrive as `{"type":"error","detail":"..."}` because once
the body has started there is no status code left to change. It shares `_assess_opportunities`
and `_public_opportunities` with the batch endpoint, so anonymity and real-terms handling cannot
drift between the two. Both write the same cache, so `GET /ai/brand-deals` replays either.

Both brand-deal endpoints order campaigns by the creator's own `category` first, then by
recency. The run is capped at `AI_MAX_BRANDS_PER_RUN`, so this decides what a creator sees at
all — not just the order.

`POST /ai/discover-creators` takes **either** `campaign_id` **or** `niche`; a body with neither is
a `422`. With `campaign_id` the server reads niche, goal, location, platforms and `min_followers`
from that campaign and **ignores** the loose fields entirely — a stale form value can never
redirect a campaign's search. A campaign owned by another brand returns `404`, matching
`/campaigns`, so its existence is not disclosed. The response echoes `criteria_source`
(`"campaign"` / `"custom"`), `campaign_id`, `campaign_name` and `follower_floor_relaxed`.

Response shapes are in `backend/app/modules/ai/schemas.py` and mirrored as TS types in the frontend pages (not in `lib/ai.ts`, which is untyped).

---

## Admin — `/admin` ✅ properly guarded

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/admin/stats` | JWT + ADMIN | Counts by role |
| GET | `/admin/users` | JWT + ADMIN | Paginated list; `role`, `search`, `page`, `page_size` |
| GET | `/admin/users/{id}` | JWT + ADMIN | Detail incl. profile fields |
| POST | `/admin/users` | JWT + ADMIN | Create BRAND/INFLUENCER only |
| DELETE | `/admin/users/{id}` | JWT + ADMIN | Cascade delete; refuses to delete an ADMIN |

This is the only module using a proper `Depends(require_admin)` dependency rather than inline checks **[V]** — it is the pattern the rest of the codebase should follow.

**[V] Minor bug in `list_users` search:** the filter builds `User.id == int(search) if search.isdigit() else False`, passing a bare Python `False` into `or_()`. SQLAlchemy coerces it to `false`, so it works, but it is accidental — an explicit `sqlalchemy.false()` would be correct.

**[V] N+1 in `list_users`:** one extra `COUNT` query per user per page to compute `has_profile`.

**[V] `page`/`page_size` are unvalidated** — `page_size=100000` is accepted, `page=0` produces a negative offset and a database error.

---

## Health

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | None | Executes `SELECT 1`. Returns `{"status":"ok","database":"ok"}`, or 503 `{"status":"degraded"}` if the DB is unreachable. (Was a static payload that reported healthy during a total outage — fixed 2026-08-10.) |

---

## Cross-cutting

- **CORS [V]:** fixed allowlist of 5 origins in `main.py` (localhost:3000, 127.0.0.1:3000, the Vercel preview, crewaa.in, www.crewaa.in) with `allow_credentials=True` and `allow_methods/headers=["*"]`. Adding an environment requires a code change and redeploy.
- **No rate limiting, no request-size limit, no idempotency, no pagination outside `/admin/users`, no webhooks, no streaming/SSE/WebSocket.**
- **Error format** is FastAPI's default `{"detail": ...}`; the frontend axios interceptor reads `error.response.data.detail` and rethrows a plain `Error` **[V]** — which means the original HTTP status is discarded before it reaches the UI, so pages cannot distinguish a 429 from a 500.
