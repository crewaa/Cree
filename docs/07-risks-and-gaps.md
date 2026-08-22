# Crewaa — Risks, Bugs & Open Questions

> Findings from a full read of the repository at commit `5e58465`, 2026-08-10.
> Ordered by severity. Nothing here is speculative — each item cites the file it came from.
> **This document contains no secret values.**
>
> **STATUS after the 2026-08-10 hardening pass** (details: `docs/08-hardening-log.md`):
>
> | # | Item | Status |
> |---|---|---|
> | 1 | Destructive migration | ✅ **FIXED** — neutralised + idempotent repair revision; verified from zero, on the repair path, and re-run |
> | 2 | Committed DB credential | ⚠️ **PARTIAL** — removed from code and CI now blocks it; **password still needs rotating** and remains in git history |
> | 3 | Unauthenticated endpoints | ✅ **FIXED** — 30 routes, 0 unprotected, with a regression test |
> | 4 | Setup tokens as access tokens | ✅ **FIXED** — plus `is_active`, password strength, set-password guard |
> | 5 | YouTube session leak | ✅ **FIXED** |
> | 6 | YouTube cross-account upsert | ✅ **FIXED** |
> | 7 | Frontend wrong-id scrape | ✅ **FIXED** |
> | 8 | Unvalidated LLM creator_id | ✅ **FIXED** |
> | 9 | Blocking I/O in async handlers | ✅ **FIXED** — Apify and Gemini go through `run_in_threadpool` |
> | 10 | AI endpoints do not scale | ✅ **FIXED** — N+1 removed, candidates filtered and capped, bounded concurrency |
> | 11 | Prompt injection / anonymity | ✅ **FIXED** — fenced data blocks + anonymity now enforced and tested, not just requested |
> | 12 | No tests / CI | ✅ **FIXED** — 86 tests + GitHub Actions (incl. schema-drift and secret scanning) |
> | 13 | No observability | ✅ **MOSTLY** — loguru, request ids, access logs, real `/health`. No error-tracking service yet |
> | 14 | Fire-and-forget background tasks | ✅ **FIXED** — `scrape_jobs` + status endpoints; failures now visible to the user |
> | 15 | Dead code | ✅ **FIXED** — removed, each verified unreferenced |
> | 16 | Data-model hygiene | ✅ **MOSTLY** — unique constraint added; JSONB migration and snapshot retention still open |
> | 17 | Config / deployment | ✅ **FIXED** — CORS from env, Dockerfile, setup script, CI |
>
> Full detail: `docs/08-hardening-log.md`.

---

## 🔴 P0 — Fix before anything else

*(Items 2–4 below are now addressed; the original analysis is kept for context.)*

### 1. A migration silently drops `saved_creators`

**File:** `backend/app/migrations/versions/dd173ce633c3_add_caching_columns_to_creatorprofile.py`

The revision is titled *"Add caching columns to CreatorProfile"*. Its `upgrade()` does:

```python
op.drop_index(op.f('ix_saved_creators_brand_id'), table_name='saved_creators')
op.drop_index(op.f('ix_saved_creators_creator_id'), table_name='saved_creators')
op.drop_table('saved_creators')
```

No later revision recreates it. This is an unreviewed `--autogenerate` artifact from a moment when `SavedCreator` was not imported into the metadata.

**Impact:** running `alembic upgrade head` on a database that is behind this revision **destroys the brand↔creator match table**. A fresh environment built from migrations will be missing a table the application requires.

**Evidence it already caused pain:** `backend/fix_alembic.py` exists solely to force `alembic_version` back to `c4a1b2d9e6f0`, and revision `8230328dad8f` is a deliberate no-op whose comment reads *"Columns already added by f9ca5e8aed1b — no-op to fix broken migration chain"*.

**Do not run migrations against production until this is resolved.**

**Suggested fix (low risk):**
1. Connect read-only to production, record `SELECT version_num FROM alembic_version` and the real schema.
2. Edit `dd173ce633c3.upgrade()` to a `pass` with a comment explaining why (rewriting an already-applied migration's body is acceptable here precisely because it must never run again).
3. Add a new head revision that creates `saved_creators` **only if it does not exist**, so fresh environments converge with production.
4. Verify by building a scratch database from scratch: `alembic upgrade head` → diff against `Base.metadata`.

---

### 2. Live database credentials committed to git — ⚠️ PARTIALLY RESOLVED

> **Code side done 2026-08-10:** `alembic.ini` no longer holds a connection string.
> **Still required: rotate the password in the Neon console.** Steps in `docs/08-hardening-log.md`.

**File:** `backend/alembic.ini`, line 3.

`sqlalchemy.url` contains a complete Neon Postgres connection string including the role name and password, in plaintext, tracked in git, present in the full history.

**Impact:** anyone with repository access — now or ever, including anyone who forks/clones — has direct read/write access to the production database. `backend/.gitignore` correctly excludes `.env`, which makes this leak look accidental rather than intentional.

**Fix, in order:**
1. **Rotate the Neon password immediately.** Assume the current one is compromised.
2. Replace the `alembic.ini` value with a placeholder and read the URL from the environment in `app/migrations/env.py`:
   ```python
   config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", "+psycopg2"))
   ```
3. Purge from history if the repository is or ever becomes public (`git filter-repo`), coordinating with anyone holding a clone.
4. Audit Neon access logs for the exposure window.

Also check `GEMINI_API_KEY`, `APIFY_TOKEN` and `YOUTUBE_API_KEY` — they are `.env`-only in the current tree, but `validate_setup.py` prints a partial YouTube key to stdout, so scrub any pasted terminal output.

---

### 3. Unauthenticated endpoints, including one that lets anyone modify any creator's profile — ✅ RESOLVED 2026-08-10

**Files:** `app/modules/users/router.py`, `app/modules/instagram/routes/instagram.py`, `app/modules/youtube/routes.py`

| Endpoint | Exposure |
|---|---|
| `PUT /users/creator-profile/{user_id}` | 🔴 **Any unauthenticated caller can overwrite any creator's name, location, category, bio and social handles.** |
| `GET /users/creator-profile/{user_id}` | Any creator's profile readable by id |
| `POST /instagram/scrape/{user_id}` | Anyone can trigger paid Apify runs — unlimited |
| `GET /instagram/analytics/{user_id}` | Full IG analytics for any creator, enumerable by id |
| `POST /youtube/scrape/{user_id}` | Anyone can burn the YouTube API daily quota (~100 requests exhausts it) |
| `GET /youtube/analytics/{user_id}` | Full YT analytics for any creator |

The PUT is the worst: changing a victim's `instagram_username` also redirects their scraping, poisoning the data that feeds brand discovery.

The cost endpoints are the most immediately expensive: Apify bills per actor run, and there is no rate limit, no auth, and no spend cap.

**Fix:**
- Add `current_user: User = Depends(get_current_user)` to every route above.
- Ownership check: `if current_user.id != user_id and current_user.role != "ADMIN": raise HTTPException(403)`.
- `PUT /users/creator-profile/{user_id}` should almost certainly just be deleted — the authenticated `PUT /users/creator-profile` already does the same job. Its only consumer is `components/dashboard/creator-profile-form.tsx`, which needs a one-line change.
- Adopt the existing-but-unused `require_roles()` helper from `app/common/dependencies.py`, and follow the `admin` module's `Depends(require_admin)` pattern.

---

### 4. Setup tokens are accepted as access tokens — ✅ RESOLVED 2026-08-10

**Files:** `app/modules/auth/service.py`, `app/common/dependencies.py`

`create_setup_token()` issues a JWT signed with the **same** `JWT_SECRET_KEY` as access tokens, carrying `{purpose, email, role, exp}` — notably **no `sub` claim**.

`get_current_user()` decodes with the same key and only reads `payload.get("sub")`. Because the setup token has no `sub`, it currently fails with "Invalid token" — so today this is safe **by accident**, not by design. Any future change that adds `sub` to the setup token, or that falls back to `email`, opens a full authentication bypass: a 10-minute token handed out on Google sign-in *before* the account is secured would become a session token.

**Fix:** make it explicit and defensive.
- Add `"type": "access"` to access tokens and require it in `get_current_user()`.
- Reject any token where `purpose == "set_password"` in `get_current_user()`.
- Better: sign setup tokens with a separate secret.

Related, in the same area:
- **`set_password_service` does not check whether the user already has a password.** It looks up by email from the token and overwrites `hashed_password` unconditionally. Combined with `google_auth` CASE 2 — which issues a setup token to *any* existing password-less user — the flow is currently sound, but the missing guard is one refactor away from becoming an account-takeover path. Add `if user.hashed_password: raise HTTPException(400)`.
- **`is_active` is never checked.** `get_current_user()` ignores it, so a deactivated user retains full access. The admin console has no deactivate action, so nothing sets it today — but the field implies a control that does not exist.
- **No password strength requirement, no email verification, no login rate limiting.**

---

## 🟠 P1 — Correctness bugs

### 5. YouTube background task uses a closing DB session — ✅ RESOLVED 2026-08-10

**File:** `app/modules/youtube/routes.py`

```python
background_tasks.add_task(scrape_and_store_youtube, user_id, db)
```

`db` is the request-scoped session from `Depends(get_db)`. FastAPI closes it when the response is returned, while the background task is still using it. Instagram's equivalent correctly opens its own session with `async with AsyncSessionLocal()`.

**Fix:** change `scrape_and_store_youtube` to open its own session, mirroring `instagram_scrapper.scrape_and_store`.

### 6. YouTube channel upsert crosses account boundaries — ✅ RESOLVED 2026-08-10

**File:** `app/modules/youtube/service.py`

The upsert matches on `channel_id` alone — `youtube_channels.channel_id` is globally unique with no `user_id` in the lookup. If two users claim the same channel, the second scrape **overwrites the first user's channel row** and then writes videos under the second user's `user_id` while the channel row still belongs to the first.

**Fix:** scope the lookup to `(user_id, channel_id)` and drop the global unique constraint, or explicitly decide that a channel can only be claimed once and reject the second claim.

### 7. Frontend passes the wrong id to the scrape endpoints — ✅ RESOLVED 2026-08-10

**File:** `frontend/app/(app)/dashboard/profile/page.tsx`

`api.post('/instagram/scrape/${savedProfile.id}')` sends `creator_profiles.id` where the backend expects `users.id`. Full analysis in `docs/06-frontend.md` §4.

**Fix:** delete both calls — the server already queues the Instagram scrape in `POST/PUT /users/creator-profile`. Add an equivalent server-side background task for YouTube, which is currently missing.

### 8. `saved_creators` is written from unvalidated LLM output — ✅ RESOLVED 2026-08-10

**File:** `app/modules/ai/router.py`

`c_id_int = int(c.get("creator_id"))` — taken straight from Gemini and used as a foreign key. A hallucinated non-existent id raises an FK violation on `commit()` and **loses the entire discovery result**; a hallucinated-but-real id silently persists a false match. A non-numeric string raises an unhandled `ValueError` → 500.

**Fix:** validate every returned `creator_id` against the set that was actually sent, and skip anything unrecognised.

### 9. Blocking I/O inside async handlers

- `apify_client.call()` is synchronous, executed inside an async background task — it blocks the event loop for the whole actor run (tens of seconds).
- `genai.generate_content()` is synchronous and runs inside every AI request handler.

**Fix:** wrap both in `fastapi.concurrency.run_in_threadpool`, or move to the async client where one exists.

### 10. AI endpoints do not scale

`POST /ai/discover-creators` sends every creator in one prompt (plus N+1 queries). `POST /ai/brand-deals` makes one Gemini call per brand with a 2-second sleep between each, inside a single HTTP request. Detail in `docs/05-ai-system.md` §5. Both need to become background jobs.

### 11. Prompt injection and brand-anonymity leakage

Scraped Instagram bios and captions are interpolated raw into every prompt, and the anonymity guarantee of the Brand Deals feature rests entirely on one instruction line with no output validation. Detail in `docs/05-ai-system.md` §3. This is a product-promise risk, not just a technical one.

---

## 🟡 P2 — Operability

### 12. No tests, no CI, no type-checking
`pytest` and `pytest-asyncio` are declared and unused; zero test files exist. No GitHub Actions, no pre-commit, no mypy. Every change to a production system currently ships unverified.

**Suggested first tests** (highest value per line): auth flows, the role guard on each endpoint, `extract_json` against malformed model output, and the scraper field mappers against recorded Apify/YouTube fixtures.

### 13. No observability — ✅ PARTIALLY RESOLVED 2026-08-10 (loguru + real /health; no error tracking yet)
No structured logging (the backend uses `print()` with emoji; `loguru` is declared and never imported), no error tracking, no metrics, no request IDs. `GET /health` returns a static `{"status":"ok"}` without touching the database, so it will report healthy during a total outage.

**Minimum viable fix:** replace `print` with `loguru`, add Sentry (or equivalent) to both apps, and make `/health` execute `SELECT 1`.

### 14. Background tasks are fire-and-forget with no record
Scrapes run in-process via `BackgroundTasks`. A deploy or crash loses them silently. There is no job table, no status, no retry, and the API returns `{"status": "scraping"}` unconditionally — even for a user that does not exist. The frontend polls and eventually gives up with no explanation.

### 15. Dead and broken code
Listed in full in `CLAUDE.md`. The important ones: the Celery worker (Celery is not a dependency), the cron script (queries a nonexistent field), the Redis cache (imported nowhere), `youtube_extractor.py` (needs `googleapiclient`, raises at import), and `validate_setup.py` (reads a config field that no longer exists).

Either delete these or fix them — right now they misrepresent the system's capabilities to anyone reading it, and the Celery/Redis pair in particular suggests async job processing exists when it does not.

### 16. Data-model hygiene
- No unique constraint on `saved_creators(brand_id, creator_id)` — application-level dedup only, racy under concurrency.
- Instagram snapshots grow forever with no retention policy.
- The `instagram_posts ↔ instagram_profiles` join is on exact `scraped_at` equality rather than a foreign key.
- `is_completed` on both profile tables defaults to `True` and is never set to `False` — it carries no information but is surfaced in the admin UI as if it does.
- `users.instagram_username` is vestigial and duplicates `creator_profiles.instagram_username`.
- AI results live as JSON strings in TEXT columns — unqueryable. JSONB would cost nothing to adopt.
- `*_generated_at` timestamps are written and never read, so caches have no TTL and no staleness signal.

### 17. Configuration and deployment
CORS origins are hard-coded in `main.py` — a new environment needs a code change. There is no Dockerfile, no CI, no IaC, and no documented deployment procedure for the backend. `ENV` is read from config and never branched on. `REDIS_URL` and `REFRESH_TOKEN_EXPIRE_DAYS` are configured but unused.

---

## Remaining order of work

Steps 2 and 4–6 of the original plan are done. What is left:

1. **Rotate the leaked Neon credential** (§2) — manual, in the Neon console. The code is ready for it.
2. **Report production `alembic_version` and whether `saved_creators` exists**, then neutralise the destructive migration (§1).
3. **Add error tracking** (Sentry or equivalent) on both apps to finish §13.
4. **Write the first tests** (§12): auth boundaries, role guards, `extract_json` against malformed output, scraper field mappers against recorded fixtures.
5. **Move the AI endpoints to background jobs** (§10) and wrap blocking Gemini/Apify calls in `run_in_threadpool` (§9).
6. **Address prompt injection and verify brand anonymity** (§11) — needs an eval fixture set first, since there is currently no way to detect a regression.
7. Add rate limiting, then clean up dead code and data-model hygiene (§15, §16).

---

## Open questions for Vishal

**Infrastructure**
1. Where is the FastAPI backend actually hosted, and how is it deployed? Nothing in the repo answers this.
2. Is there any monitoring or error tracking configured outside the repository?
3. Does production still have the `saved_creators` table, and what is the current `alembic_version`?
4. Are there other environments (staging?), and does anything besides Vercel + Neon exist?

**Product**
5. Is the auto-save of every ranked creator into `saved_creators` intended, or should saving be an explicit brand action?
6. What is meant to happen after a creator sees an opportunity — is closing that loop the next feature?
7. Was the earlier ChatGPT project holding prompts, specs, or roadmap documents that are not in this repo? The handoff file references project instructions and knowledge that never made it across.

**Priorities**
8. Is the immediate goal hardening what exists, or shipping the next feature? The findings above lean strongly toward a short hardening pass first — items 1–5 are a day or two of work and remove every finding that can cost money or leak data.
