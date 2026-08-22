import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.core.observability import capture, init_error_tracking, note_request
from app.modules.scraping.service import reap_stalled_jobs
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.users.router import router as users_router
from app.modules.instagram.routes.instagram import router as instagram_router
from app.modules.youtube.routes import router as youtube_router
from app.modules.ai.router import router as ai_router
from app.modules.admin.router import router as admin_router
from app.modules.campaigns.router import router as campaigns_router


# Before the app is built, so the ASGI integration wraps everything below.
_error_tracking_enabled = init_error_tracking()

app = FastAPI(title=settings.app_name)

# Origins come from config (CORS_ORIGINS, comma-separated) so that adding an
# environment is a config change rather than a code deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """
    Attach a request id and emit one structured access log line per request.

    Without this there is no way to correlate a user's report with server logs,
    and no visibility into which endpoints are slow.
    """
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    # Same id as the access log line below, so an issue points at real logs.
    note_request(request_id)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "request_id={} {} {} -> unhandled exception after {:.1f}ms",
            request_id, request.method, request.url.path, duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id

    # Health checks are frequent and uninteresting; keep them at debug.
    log = logger.debug if request.url.path == "/health" else logger.info
    log(
        "request_id={} {} {} {} {:.1f}ms",
        request_id, request.method, request.url.path,
        response.status_code, duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all so an unexpected error returns a clean JSON body and a traceable
    id, instead of leaking a stack trace or an empty 500 to the browser.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("request_id={} unhandled error on {}", request_id, request.url.path)
    # Handling the exception here stops it propagating to the ASGI integration,
    # so report it explicitly or the tracker stays silent. See observability.capture.
    capture(exc, request_id)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again.",
            "request_id": request_id,
        },
    )


@app.on_event("startup")
async def log_startup_configuration():
    """Surface which optional integrations are actually usable at boot."""
    missing = [
        name for name, value in (
            ("GEMINI_API_KEY", settings.gemini_api_key),
            ("APIFY_TOKEN", settings.apify_token),
            ("YOUTUBE_API_KEY", settings.youtube_api_key),
        ) if not value
    ]
    logger.info("{} starting (env={})", settings.app_name, settings.env)
    # Said out loud because a tracker everyone believes is running, but which is
    # silently disabled, is worse than having none at all.
    logger.info(
        "Error tracking {}",
        "enabled" if _error_tracking_enabled else "disabled (no SENTRY_DSN)",
    )
    if missing:
        logger.warning(
            "Optional integrations disabled, missing config: {}", ", ".join(missing)
        )

    # Scrapes are in-process background tasks, so anything a previous process
    # had in flight died with it. Clear those out now rather than leaving
    # creators watching a spinner that resolves only when they happen to poll.
    try:
        async with AsyncSessionLocal() as db:
            await reap_stalled_jobs(db)
    except Exception as e:
        # Never let housekeeping stop the app from booting.
        logger.warning("Startup scrape-job sweep failed: {}", e)


app.include_router(auth_router)
app.include_router(health_router)
app.include_router(users_router)
app.include_router(instagram_router)
app.include_router(youtube_router)
app.include_router(ai_router)
app.include_router(admin_router)
app.include_router(campaigns_router)
