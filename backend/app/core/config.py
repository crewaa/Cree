from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    
    app_name: str
    env: str
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int

    google_client_id: str
    
    # Apify Instagram Scraping (direct SDK)
    apify_token: str = ""
    
    # Redis cache
    redis_url: str = "redis://localhost:6379/0"
    
    # YouTube API
    youtube_api_key: str = ""

    # Gemini AI Engine
    gemini_api_key: str = ""
    #: Model id. Kept in config so it can be changed without a code deploy —
    #: model changes are high-risk and may need to be rolled back quickly.
    gemini_model: str = "gemini-2.5-flash"
    #: Hard timeout for a single Gemini call, in seconds. Without this a hung
    #: request holds a worker until the client gives up.
    gemini_timeout_seconds: int = 60
    #: Max creators serialised into one discovery prompt. Beyond this the prompt
    #: approaches the context limit and quality degrades.
    ai_max_creators_per_prompt: int = 40
    #: Max brands fanned out over in one brand-deals run.
    ai_max_brands_per_run: int = 12
    #: How many Gemini calls may be in flight at once during that fan-out.
    ai_max_concurrent_calls: int = 4
    #: After this many days a cached AI result is shown as stale so the creator
    #: knows it predates their current numbers. `*_generated_at` was previously
    #: written and never read, so a cache could be months old with no signal.
    ai_cache_stale_after_days: int = 14

    #: bcrypt cost factor. Each step doubles the work: 12 is ~180ms on a laptop
    #: and noticeably more on a small shared instance. Lower it to 11 or 10 if
    #: sign-in feels slow in production — existing passwords keep working,
    #: because bcrypt records the cost inside each hash. Do not go below 10.
    bcrypt_rounds: int = 12

    #: Failed sign-in attempts allowed for one email+IP pair before a temporary
    #: lockout. Counted on failures only: a correct password is never refused
    #: for being "too many requests", which the previous IP-wide throttle did.
    login_max_failures: int = 8
    #: How long that lockout lasts, in seconds.
    login_failure_window_seconds: int = 900

    #: A scrape still marked "running" after this long is treated as dead.
    #: Scrapes are in-process background tasks, so a deploy or crash strands them
    #: as "running" forever and the creator watches a spinner that will never
    #: resolve. Age-based rather than "everything running at startup", which
    #: would be wrong the moment a second instance exists. Must comfortably
    #: exceed the slowest legitimate scrape (Apify runs take well under a minute).
    scrape_stuck_after_minutes: int = 15

    #: How long Instagram snapshots are kept. Each scrape appends a profile row
    #: plus up to 15 posts, forever — this bounds that growth. 0 disables pruning.
    scrape_ttl_days: int = 90

    #: Sentry DSN. Blank disables error tracking entirely — the app runs
    #: identically without it, so local development and CI need no account.
    sentry_dsn: str = ""
    #: Defaults to `env` so issues are separated into dev/staging/production
    #: without a second setting to remember.
    sentry_environment: str = ""
    #: Optional version marker (a git sha works) so an issue can be tied to a
    #: deploy. Blank means Sentry groups everything under one release.
    sentry_release: str = ""
    #: Performance tracing is billed separately from errors. Off by default so
    #: turning it on is a decision, not a surprise.
    sentry_traces_sample_rate: float = 0.0

    # CORS — comma-separated list of allowed origins.
    # Overridable per environment so adding a domain is not a code change.
    cors_origins: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "https://crewaa-m4pz.vercel.app,"
        "https://crewaa.in,"
        "https://www.crewaa.in"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
