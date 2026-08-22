"""
Request rate limiting.

Guards three things that were previously unbounded:

  * credential endpoints, against password brute-forcing
  * scrape endpoints, which cost money (Apify) and quota (YouTube Data API)
  * AI endpoints, which cost Gemini quota

Implementation is a fixed-window counter held in process memory.

    LIMITATION: the counter is per-process. Running multiple uvicorn workers or
    multiple instances multiplies the effective limit by the number of
    processes. That is an acceptable trade for a control that needs no new
    infrastructure, and it still blocks the abusive cases these limits exist
    for. If Crewaa moves to several instances, swap `_Counter` for a Redis
    INCR+EXPIRE against `settings.redis_url` — the dependency signature here
    does not need to change.
"""

import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, HTTPException, Request, status

from app.common.dependencies import get_current_user
from app.core.logging import logger
from app.modules.users.models import User


class _Counter:
    """Fixed-window request counter keyed by an arbitrary string."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()
        self._last_sweep = time.monotonic()

    def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """
        Record a request. Returns (allowed, seconds_until_reset).
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            # Periodically drop keys nobody is using so memory cannot grow
            # without bound from one-off IPs.
            if now - self._last_sweep > 300:
                for k in list(self._hits):
                    self._hits[k] = [t for t in self._hits[k] if t > cutoff]
                    if not self._hits[k]:
                        del self._hits[k]
                self._last_sweep = now

            timestamps = [t for t in self._hits[key] if t > cutoff]

            if len(timestamps) >= limit:
                self._hits[key] = timestamps
                retry_after = max(1, int(window_seconds - (now - timestamps[0])))
                return False, retry_after

            timestamps.append(now)
            self._hits[key] = timestamps
            return True, 0


_counter = _Counter()


def _client_ip(request: Request) -> str:
    """
    Best-effort client identity.

    Behind a proxy the socket address is the proxy, so X-Forwarded-For is
    preferred. That header is client-controllable when NOT behind a trusted
    proxy, so this is a throttling signal, never an authorisation one.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limit: int, window_seconds: int, scope: str):
    """
    Throttle by client IP. For endpoints reachable without authentication.

        @router.post("/login", dependencies=[rate_limit(5, 60, "login")])
    """
    # Distinct name: the route-auth audit in tests/test_authorization.py
    # identifies guards by function name, and a rate limiter must never be
    # mistaken for an authentication dependency.
    async def _rate_limit_ip_checker(request: Request) -> None:
        key = f"{scope}:{_client_ip(request)}"
        allowed, retry_after = _counter.hit(key, limit, window_seconds)
        if not allowed:
            logger.warning("Rate limit hit on '{}' by {}", scope, _client_ip(request))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

    return Depends(_rate_limit_ip_checker)


def rate_limit_user(limit: int, window_seconds: int, scope: str):
    """
    Throttle by authenticated user id — the right key for endpoints that spend
    money, since an attacker can rotate IPs but not user accounts for free.

        @router.post("/scrape", dependencies=[rate_limit_user(5, 3600, "scrape")])
    """
    async def _rate_limit_user_checker(current_user: User = Depends(get_current_user)) -> None:
        key = f"{scope}:user:{current_user.id}"
        allowed, retry_after = _counter.hit(key, limit, window_seconds)
        if not allowed:
            logger.warning("Rate limit hit on '{}' by user {}", scope, current_user.id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "You have made too many requests. "
                    f"Please try again in about {max(1, retry_after // 60)} minute(s)."
                ),
                headers={"Retry-After": str(retry_after)},
            )

    return Depends(_rate_limit_user_checker)


# ---------------------------------------------------------------------------
# Failure-counted lockout
#
# A plain `rate_limit` on /login counts *every* attempt, which produces the
# worst possible behaviour: someone mistypes their password a few times, finally
# types it correctly, and is told "Too many requests". Their credentials were
# right and the product refused them anyway — indistinguishable, from the user's
# side, from the app being broken.
#
# Counting only failures fixes that. A correct password is never refused, while
# a guesser still runs out of attempts. Keyed on email *and* IP so one attacker
# cannot lock a real user out of their own account by guessing at it from
# somewhere else.
# ---------------------------------------------------------------------------

_failures = _Counter()


def _failure_key(email: str, ip: str) -> str:
    return f"login_fail:{email.strip().lower()}:{ip}"


def check_login_allowed(request: Request, email: str, limit: int, window: int) -> None:
    """Raise 429 if this email+IP pair has failed too often. Records nothing."""
    key = _failure_key(email, _client_ip(request))
    with _failures._lock:
        now = time.monotonic()
        recent = [t for t in _failures._hits.get(key, []) if t > now - window]
        _failures._hits[key] = recent
        if len(recent) >= limit:
            retry_after = max(1, int(window - (now - recent[0])))

    if len(recent) >= limit:
        logger.warning("Login lockout for {} from {}", email, _client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many failed sign-in attempts. Please try again in about "
                f"{max(1, retry_after // 60)} minute(s), or reset your password."
            ),
            headers={"Retry-After": str(retry_after)},
        )


def record_login_failure(request: Request, email: str, window: int) -> None:
    """Count one failed attempt."""
    _failures.hit(_failure_key(email, _client_ip(request)), limit=10**9, window_seconds=window)


def clear_login_failures(request: Request, email: str) -> None:
    """Forget past failures after a successful sign-in."""
    with _failures._lock:
        _failures._hits.pop(_failure_key(email, _client_ip(request)), None)


def reset_for_tests() -> None:
    """Clear all counters. Used by the test suite between cases."""
    with _counter._lock:
        _counter._hits.clear()
    with _failures._lock:
        _failures._hits.clear()
