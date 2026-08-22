"""
Guard: the test suite must never talk to the real Sentry project.

`Settings` reads `backend/.env`, which on a developer's machine holds the live
DSN. Tests deliberately raise exceptions and log errors, and the loguru
integration turns `logger.error(...)` into a Sentry event — so without the
override in `conftest.py` a single `pytest` run would file dozens of fake issues
against production and eat a month's free quota.

This is a one-line invariant that is easy to undo by accident, which is exactly
what a test is for.
"""

from app.core.config import settings


def test_the_suite_runs_with_error_tracking_disabled():
    assert settings.sentry_dsn == "", (
        "The test suite has a live Sentry DSN. Every deliberate failure below "
        "is about to be reported as a production issue. See conftest.py."
    )


def test_the_app_did_not_initialise_a_live_client():
    """Belt and braces: check the SDK itself, not just the setting."""
    import sentry_sdk

    client = sentry_sdk.get_client()
    dsn = getattr(client, "dsn", None)
    assert not dsn, f"a live Sentry client is active during tests: {dsn}"
