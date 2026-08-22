# Crewaa — Product Understanding

> Derived entirely from the code at commit `5e58465`. No product spec exists in the repo, so
> everything below is reconstructed from routes, UI copy, and data flow.
> **[V]** verified · **[I]** inferred · **[?]** unknown.

---

## 1. One-sentence definition

**[I]** Crewaa is a two-sided AI marketplace where **brands** find creators for campaigns and **creators** find brand deals, with Google Gemini doing the matching on top of scraped Instagram and YouTube performance data.

The landing page copy positions it as "Platform for brands and creators" **[V]** (`frontend/app/layout.tsx` metadata).

---

## 2. Personas

### Creator / Influencer (`role = "INFLUENCER"`)
Signs up, fills in a creator profile with their Instagram and/or YouTube handle. Crewaa scrapes their public metrics. They then get two AI tools:

- **AI Growth Analyzer** — a structured read of their profile: summary, strengths, improvement areas, best-fit brand categories, recommended content formats.
- **Brand Deals** — a feed of **anonymised** opportunities generated from real brand profiles in the database. The AI is explicitly instructed to strip brand name, contact, website and email.

A third card, **Creator Support** (human content-production services), is shown as "Coming Soon" **[V]**.

### Brand (`role = "BRAND"`)
Signs up, fills in a brand profile (industry, campaign goal, budget band, target location/languages, platform preferences). Their one live tool:

- **Discover Creators** — submit campaign requirements, get an AI-ranked list of creators with fit level (High/Medium/Low), reasoning, risks and a recommended campaign type. Results are automatically persisted to `saved_creators` and surface on the brand dashboard.

Two cards, **AI Influencer** (AI-generated virtual influencers) and **AI Marketing Suite**, are "Coming Soon" **[V]**.

### Admin (`role = "ADMIN"`)
Cannot be created through signup **[V]** — `signup_user()` rejects the ADMIN role, and admins are seeded via `python seed_admin.py`. Admins get platform stats and full user CRUD, but **cannot delete other admins** **[V]** (`admin/service.py:delete_user`).

---

## 3. Core user journeys

### Creator journey
```
/signup → choose "Influencer" → /signup/influencer
  (email+password, or Google Sign-In → /set-password)
→ /dashboard/influencer            "Creator Studio"
→ /dashboard/profile               fill creator profile
   └─ saving with an IG username fires a background Instagram scrape
   └─ the UI separately POSTs /instagram/scrape and /youtube/scrape
→ /dashboard/analytics/influencer  IG + YT tabs with charts
→ /dashboard/influencer/growth-analyzer   POST /ai/creator-summary
→ /dashboard/influencer/deals             POST /ai/brand-deals
```

### Brand journey
```
/signup → choose "Brand" → /signup/brand
→ /dashboard/brand                 "Brand Studio"
→ /dashboard/brand-profile         fill brand profile
→ /dashboard/brand/discover        POST /ai/discover-creators
   └─ ranked creators are written to saved_creators as a side effect
→ /dashboard/analytics/brand       brand snapshot + saved creator list
```

### Admin journey
```
login → (app)/layout redirects ADMIN to /dashboard/admin
→ /dashboard/admin                 platform stats
→ /dashboard/admin/users           paginated, filterable, searchable user list
→ /dashboard/admin/users/[id]      detail; create / delete users
```

---

## 4. Core entities

| Concept | Table | Notes |
|---|---|---|
| Account | `users` | one row per human; role decides everything downstream |
| Creator profile | `creator_profiles` | 1:1 with user; also caches AI output |
| Brand profile | `brand_profiles` | 1:1 with user |
| Creator↔Brand match | `saved_creators` | written by the AI discovery run, not by an explicit "save" action |
| Social snapshot | `instagram_profiles`, `instagram_posts`, `youtube_channels`, `youtube_videos` | scraped public data |

---

## 5. Product observations worth flagging

**[V] "Saved creators" is a misleading name.** Nothing in the UI lets a brand explicitly save a creator. The table is populated as a *side effect* of `POST /ai/discover-creators` — every creator the AI returns is upserted, regardless of fit level. So the brand dashboard's "saved creators" is really "creators from your last discovery run", including Low-fit ones.

**[V] Brand Deals fans out over every brand in the database.** `POST /ai/brand-deals` loops over *all* `brand_profiles` and makes one Gemini call per brand, sleeping 2 seconds between each. With 50 brands that is 50 API calls and ~100s of sleep inside a single HTTP request. This will time out well before the platform is large.

**[V] Discover Creators sends every creator to the model in one prompt.** `select(CreatorProfile)` with no filter, no pagination, no pre-filter on niche or platform — the entire creator base plus their recent posts is serialised into one Gemini prompt. This breaks on context limits as the platform grows.

**[V] There is no messaging, application, contract, or payment flow.** A creator can see an opportunity but has no way to act on it. A brand can see a ranked creator but has no way to contact them. The marketplace loop is not closed in code.

**[V] There is no notion of a campaign entity.** Campaign details live only in the request body of a single `/ai/discover-creators` call and are never persisted. The brand's *profile* holds a single `campaign_goal` / `budget_range`, so a brand effectively has one implicit campaign.

**[V] `pricing: "Mid"` is hard-coded** for every creator in the AI payload (`ai/router.py:_build_creator_payload`), with the comment "default for now". Budget matching is therefore not real.

**[?] Monetisation is undefined.** No billing, no plans, no payment integration, no credits — nothing in the repo touches money.

**[?] Compliance/geography.** `target_location` defaults to `"India"` and `target_languages` to `["English"]` **[V]**, and the domain is `.in`, which suggests an India-first launch **[I]**. No GDPR/DPDP handling, consent capture, or data-retention logic exists. There *are* `/privacy` and `/terms` pages on the marketing site — their content should be checked against what the platform actually does with scraped third-party data.

---

## 6. Open product questions for Vishal

1. Is `saved_creators` meant to be an explicit brand action, or is the auto-save on discovery intentional?
2. How is a deal supposed to progress after a creator sees an opportunity — is that the next thing to build?
3. Should discovery filter creators in SQL (niche, platform, follower band) before hitting the AI, rather than sending everyone?
4. Is Crewaa monetising, and if so how — take rate, subscription, or lead fees?
5. What is the intended source of truth for creator pricing, given it is currently hard-coded to "Mid"?
