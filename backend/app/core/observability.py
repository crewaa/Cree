"""
Error tracking.

Disabled unless `SENTRY_DSN` is set, so this is a no-op in development, in
tests, and for anyone who has not signed up. Nothing else in the app needs to
know whether it is on.

This file is longer than a call to `sentry_sdk.init()` for one reason: by
default Sentry attaches the **local variables of every stack frame** to an
event. In this codebase those locals include the Neon connection string, the
JWT signing key, the Gemini and Apify tokens, scraped Instagram bios — and, in
the opportunity pipeline, the identity of the brand behind an anonymous offer.

`diagnose=False` is set on loguru for exactly that reason (rule 8 in
CLAUDE.md). Turning on an error tracker that ships frame locals to a third
party would quietly undo it, and nobody would notice until the day someone
read an issue. So the defence is three-deep:

1. `include_local_variables=False` — frame locals are never collected.
2. `send_default_pii=False` — no email addresses, no IP addresses, no cookies.
3. `_before_send` redacts anything that still looks like a credential, because
   secrets also leak through *messages*: asyncpg puts the whole connection
   string into its connection errors, and an `Authorization` header can arrive
   inside request context.

The brand-anonymity promise is a product guarantee, not just a privacy
preference, so it gets the same treatment as a password.
"""

import re
from typing import Any

from app.core.config import settings
from app.core.logging import logger

#: Substrings that mark a key as carrying a credential. Matched case-insensitively
#: against dictionary keys anywhere in the event payload.
_CREDENTIAL_HINTS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "authorization", "auth", "cookie", "session", "credential",
    "dsn", "database_url", "jwt", "private",
)

#: Keys that carry the identity of the brand behind an anonymous opportunity.
#: A creator must never learn it, and neither must an issue tracker.
_ANONYMITY_HINTS = ("brand_id", "brand_name")

REDACTED = "[redacted]"

#: `postgresql://user:password@host/db` — the password, anywhere in any string.
#: asyncpg includes the full DSN in connection errors, which is the single most
#: likely way the Neon credential would reach a third party.
_URL_CREDENTIALS = re.compile(r"(://[^:/@\s]+:)[^@\s]+(@)")

#: `Authorization: Bearer eyJ...` arriving via request context or a log message.
_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._\-]{8,}")

#: Google/Gemini keys have a recognisable prefix, so they can be caught even
#: when they appear in a bare string with no key to match against.
_API_KEY_LITERALS = re.compile(r"\b(AIza[0-9A-Za-z_\-]{20,}|apify_api_[A-Za-z0-9]{20,})")

#: Deeply nested payloads are pathological; stop rather than recurse forever.
_MAX_DEPTH = 8


def _looks_sensitive(key: str) -> bool:
    lowered = str(key).lower()
    return any(hint in lowered for hint in _CREDENTIAL_HINTS + _ANONYMITY_HINTS)


def _scrub_text(value: str) -> str:
    value = _URL_CREDENTIALS.sub(r"\1" + REDACTED + r"\2", value)
    value = _BEARER.sub(r"\1" + REDACTED, value)
    value = _API_KEY_LITERALS.sub(REDACTED, value)
    return value


def _scrub(value: Any, depth: int = 0) -> Any:
    """Walk an event and redact credentials by key and by shape."""
    if depth > _MAX_DEPTH:
        return value

    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if _looks_sensitive(key):
                cleaned[key] = REDACTED
            else:
                cleaned[key] = _scrub(item, depth + 1)
        return cleaned

    if isinstance(value, (list, tuple)):
        scrubbed = [_scrub(item, depth + 1) for item in value]
        return type(value)(scrubbed) if isinstance(value, tuple) else scrubbed

    if isinstance(value, str):
        return _scrub_text(value)

    return value


def _before_send(event: dict, _hint: dict) -> dict:
    """
    Last gate before an event leaves the process.

    Deliberately total: it walks the whole event rather than a known list of
    fields, because the fields that carry secrets change as the app changes and
    an allowlist would silently stop covering them.
    """
    try:
        return _scrub(event)
    except Exception as exc:  # pragma: no cover - defensive
        # If scrubbing fails, drop the event. Sending something unscrubbed is
        # the one outcome worse than losing an error report.
        logger.warning("Dropping a Sentry event: scrubbing failed ({})", exc)
        return None


def init_error_tracking() -> bool:
    """
    Start error tracking if a DSN is configured.

    Returns whether it was enabled, so startup can say so out loud — a tracker
    everyone believes is on but which is silently disabled is worse than none.
    """
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment or settings.env,
        release=settings.sentry_release or None,
        # See the module docstring. These two lines are the point of this file.
        include_local_variables=False,
        send_default_pii=False,
        before_send=_before_send,
        # Performance tracing is billed separately and off by default; turn it
        # on deliberately rather than discovering it on an invoice.
        traces_sample_rate=settings.sentry_traces_sample_rate,
        max_breadcrumbs=25,
        integrations=[
            StarletteIntegration(failed_request_status_codes=[range(500, 600)]),
            FastApiIntegration(failed_request_status_codes=[range(500, 600)]),
        ],
    )
    return True


def note_request(request_id: str, user_id: int | None = None) -> None:
    """
    Tag the current scope so an issue can be traced back to a log line.

    The access log already prints `request_id=...` for every request. Putting
    the same id on the Sentry event is what turns "something broke" into "here
    is the exact request, and here are the surrounding log lines".

    The user id is an internal integer, not an email address — enough to answer
    "is this one unlucky account or everyone?" without shipping personal data.
    """
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - only if the package went missing
        return

    scope = sentry_sdk.get_current_scope()
    scope.set_tag("request_id", request_id)
    if user_id is not None:
        scope.set_user({"id": str(user_id)})


def capture(exc: Exception, request_id: str) -> None:
    """
    Report an exception the app has already handled.

    Belt and braces, and worth being precise about why. sentry-sdk enables a
    loguru integration by default, so the `logger.exception(...)` in the
    catch-all handler already produces an event on its own — that was measured,
    not assumed. This call exists so reporting does not depend on that: if log
    routing is ever changed, or loguru swapped out, errors would otherwise stop
    being reported while the tracker still looked healthy.

    Both paths together still yield exactly **one** issue, because Sentry
    de-duplicates a repeat capture of the same exception object. There is a test
    asserting that count, so a future change that starts double-reporting fails
    the build rather than quietly doubling the bill.

    A side effect worth knowing: because of that loguru integration, every
    existing `logger.error(...)` in the codebase becomes a Sentry issue once a
    DSN is set, and `logger.warning(...)` becomes a breadcrumb.
    """
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover
        return

    sentry_sdk.get_current_scope().set_tag("request_id", request_id)
    sentry_sdk.capture_exception(exc)
