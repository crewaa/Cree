# Crewaa — Domain Model & Data

> Verified against `backend/app/modules/**/models.py` and `backend/app/migrations/versions/` at commit `5e58465`.

---

## 1. Entity relationship overview

```
                          ┌──────────────┐
                          │    users     │
                          │  id (PK)     │
                          │  email  UQ   │
                          │  role        │
                          └──────┬───────┘
             ┌───────────┬───────┼────────┬──────────────┬────────────┐
             │ 1:1       │ 1:1   │ 1:N    │ 1:N          │ 1:N        │ 1:N (as brand)
             ▼           ▼       ▼        ▼              ▼            ▼
   creator_profiles  brand_   instagram_ instagram_  youtube_    saved_creators
                     profiles  profiles   posts       channels     ├─ brand_id   → users.id
                                                          │        └─ creator_id → users.id
                                                          │ 1:N (by channel_id)
                                                          ▼
                                                    youtube_videos
```

Every FK to `users.id` is `ON DELETE CASCADE`, and the ORM relationships carry `cascade="all, delete-orphan"` **[V]**. Deleting a user therefore wipes their profile, all social snapshots, and all `saved_creators` rows where they are the **brand**.

**⚠️ Asymmetry [V]:** `User.saved_creators` is defined only with `foreign_keys=[SavedCreator.brand_id]`. There is no ORM-level back-reference from a *creator* to the rows where they are the `creator_id`. The DB-level `ON DELETE CASCADE` still cleans those up, but ORM-driven deletes (`await db.delete(user)`, which is what the admin console uses) rely on the database constraint rather than the ORM for that side.

---

## 2. Tables

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `email` | str, **unique**, indexed | |
| `hashed_password` | str, **nullable** | NULL ⇒ Google-only account that has not set a password |
| `role` | str | `"BRAND"` \| `"INFLUENCER"` \| `"ADMIN"` — free-text column, **no DB constraint** |
| `is_active` | bool, default true | **read but never enforced** — `get_current_user()` does not check it, so deactivating a user does nothing |
| `instagram_username` | str, nullable | **vestigial** — duplicated on `creator_profiles`, and no application code reads it |

### `creator_profiles` (1:1 with users)
| Column | Type | Notes |
|---|---|---|
| `user_id` | FK users.id, **unique**, CASCADE | |
| `full_name`, `location`, `primary_platform`, `category` | str, NOT NULL | `primary_platform` ∈ Instagram \| YouTube (by convention only) |
| `instagram_username`, `youtube_username` | str, nullable, **indexed** | drive the scrapers |
| `instagram_profile_link`, `youtube_profile_link` | str, nullable | |
| `bio` | text, nullable | |
| `ai_summary` | text, nullable | **JSON blob** — cached `CreatorSummaryResponse` |
| `summary_generated_at` | timestamptz, nullable | |
| `cached_brand_deals` | text, nullable | **JSON blob** — cached list of opportunities |
| `brand_deals_generated_at` | timestamptz, nullable | |
| `is_completed` | bool, **default True** | see note below |

**[V] `is_completed` defaults to `True` and is never set to `False` anywhere.** It is exposed to the admin console as `creator_profile_completed`, where it will always read "completed". It carries no real information.

**[V] AI results are stored as JSON strings in TEXT columns**, not JSONB. They cannot be queried, indexed, or partially updated — only read whole and re-parsed. `_safe_json_parse` swallows corruption and returns `[]`; the GET endpoints swallow it with a bare `except:` and return `null`.

### `brand_profiles` (1:1 with users)
| Column | Type | Notes |
|---|---|---|
| `user_id` | FK users.id, **unique**, CASCADE | |
| `brand_name`, `industry` | str, NOT NULL | |
| `description`, `website`, `logo_url` | nullable | `logo_url` is a plain string; **no file upload exists anywhere** |
| `campaign_goal` | str, default `"Awareness"` | Awareness \| Sales \| Engagement |
| `budget_range` | str, default `"Mid"` | Low \| Mid \| High |
| `target_location` | str, nullable | defaults to `"India"` at read time in the AI layer |
| `target_languages` | **text holding a JSON list** | |
| `platform_preferences` | **text holding a JSON list** | |
| `is_completed` | bool, default True | same non-signal as above |

### `saved_creators`
| Column | Type | Notes |
|---|---|---|
| `brand_id` | FK users.id, indexed, CASCADE | |
| `creator_id` | FK users.id, indexed, CASCADE | |
| `fit_level` | str NOT NULL | High \| Medium \| Low |
| `score_reasoning` | text holding a JSON list | |
| `saved_at` | timestamptz, server_default now() | |

**[V] There is no unique constraint on `(brand_id, creator_id)`.** Uniqueness is enforced only in application code, by pre-loading existing rows into a dict inside `discover_creators()`. Two concurrent discovery runs by the same brand will create duplicates.

**[V] `creator_id` is taken from the LLM's output** — `int(c.get("creator_id"))` in `ai/router.py`. If Gemini hallucinates a creator_id that does not exist in `users`, the insert raises a FK violation and the whole `await db.commit()` fails, losing the entire discovery result. If it hallucinates an id that *does* exist but is wrong, a bogus match is silently persisted. There is no validation that the returned id was in the set that was sent.

### `instagram_profiles` / `instagram_posts` — append-only snapshots
Both carry `user_id` + `scraped_at` (naive UTC, `TIMESTAMP WITHOUT TIME ZONE`). Reads take the newest profile by `scraped_at`, then posts whose `scraped_at` **exactly equals** that profile's.

**[V] This equality join is fragile.** Both are written from the same `now_utc` variable in one transaction, so it holds today — but any change to how timestamps are assigned silently returns zero posts. A FK from post → profile would be correct.

**[V] Unbounded growth.** Nothing ever deletes old snapshots. Each scrape adds 1 profile row + up to 15 post rows per creator, forever.

**[V] No unique constraint on `shortcode`** — re-scraping duplicates every post as a new row (by design, since it is snapshot-based, but it means post counts across the table are meaningless without filtering by `scraped_at`).

### `youtube_channels` / `youtube_videos` — upsert + replace
| | |
|---|---|
| `youtube_channels.channel_id` | str, **unique**, indexed — the upsert key |
| `youtube_videos.channel_id` | **FK → youtube_channels.channel_id** (a non-`id` FK) |
| `subscribers`, `total_views`, `videos.views/likes` | BigInteger |
| `duration` | int seconds, parsed from ISO-8601 `PT1H23M45S` |

**[V] Re-scraping deletes all previous videos for the channel.** No YouTube history is retained, unlike Instagram. The two platforms have opposite persistence models — worth unifying deliberately.

**[V] `youtube_channels.channel_id` is globally unique, not per-user.** If two Crewaa users claim the same YouTube channel, the second scrape **updates the first user's row** (the upsert matches on `channel_id` alone and never checks `user_id`), silently reassigning nothing but overwriting data across account boundaries. The videos then get written with the second user's `user_id` while the channel row still belongs to the first. This is a real cross-account data bug.

---

## 3. Migration history

15 revisions, one linear chain, **head = `cee76db5231d`**:

```
8dc7c50da286  create users
eb8943fe94e8  create creator_profiles
ab0b60e6d270  add instagram analytics
5f89fd933050  add instagram analytics tables
fe798cbf3e4e  add instagram tables
a8b57869c9d8  add IG/YT columns
22d48585032b  add IG/YT fields
e18862f1a8d4  add youtube channel + video tables
3fbacdf46b79  create youtube channel + video tables
c4a1b2d9e6f0  create brand_profiles
ede20de67a7b  add saved_creators table
dd173ce633c3  ⚠️ titled "Add caching columns" — ACTUALLY DROPS saved_creators
f9ca5e8aed1b  add the 4 caching columns (the real one)
8230328dad8f  no-op; comment says "to fix broken migration chain"
cee76db5231d  add ai_summary column   ← HEAD
```

### ⚠️ The `dd173ce633c3` problem

```python
def upgrade():
    op.drop_index(...); op.drop_index(...)
    op.drop_table('saved_creators')     # ← in a revision titled "Add caching columns"
```

This is an unreviewed `alembic revision --autogenerate` artifact: at that moment the model file did not import `SavedCreator`, so autogenerate concluded the table was orphaned and emitted a drop. **Nothing later in the chain recreates it.**

Consequences:
- A fresh `alembic upgrade head` produces a database **without** `saved_creators`, even though the model and the code require it.
- Production presumably still has the table because it was never migrated down through that revision — hence `backend/fix_alembic.py`, which force-stamps `alembic_version` to `c4a1b2d9e6f0`.
- Migration state in production and migration state in the repo are therefore **not known to agree**.

**Before touching migrations, verify the live value of `alembic_version` and diff the real schema against the models.** Do not run `alembic upgrade head` or `downgrade` against production.

Also note: `8230328dad8f`'s docstring says `Revises: 3b69128322bd` while its actual `down_revision` is `f9ca5e8aed1b` **[V]** — a leftover of manual chain surgery. And `dd173ce633c3` / `f9ca5e8aed1b` share the identical title "Add caching columns to CreatorProfile", which is how the destructive one hid in plain sight.

---

## 4. Data safety notes

- **PII stored:** email addresses, real names, locations, bios, and scraped social handles/content of creators.
- **Third-party data:** Instagram and YouTube data for creators is scraped and stored indefinitely. Instagram scraping via Apify is against Instagram's ToS **[I]** — a business risk worth a conscious decision.
- **No retention policy, no deletion request handling, no consent record.** Admin delete cascades, which is the only erasure path.
- **No soft delete, no audit log.** Admin user deletion is permanent and unrecorded.
- **No tenant isolation concept** — there are no organisations or teams; a user is the unit of ownership.
