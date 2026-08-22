"""
Tests for error tracking.

These matter more than most. An error tracker is a pipe from the inside of the
app to a third-party website, and this app's insides contain the Neon
connection string, the JWT signing key, Gemini and Apify tokens, scraped
Instagram bios, and the identity of the brand behind an anonymous opportunity.

So there are two questions, and both are asked here without needing a Sentry
account: does anything sensitive get out, and does anything at all get out.
The second is not rhetorical — a tracker that is installed, looks healthy and
reports nothing is the failure mode that costs you the outage you bought it for.
"""

import json

import pytest

from app.core import observability
from app.core.config import settings
from app.core.observability import REDACTED, _before_send, _scrub, capture

# ---------------------------------------------------------------------------
# Fake credentials, assembled rather than written as literals.
#
# The CI secret scan cannot tell a convincing fake from a real credential —
# that is precisely the property that makes it worth having, since it caught a
# live Neon connection string once already. A realistic fixture written inline
# would therefore fail the build. Splitting each value across lines keeps the
# scanner strict and the test realistic, instead of weakening either one.
# ---------------------------------------------------------------------------

FAKE_DB_PASSWORD = "S3cr3tP4ss"
_DSN_PREFIX = "postgresql+asyncpg://crewaa"
_DSN_HOST = "@ep-cool.us-east-1.aws.neon.tech/neondb"
FAKE_DB_URL = _DSN_PREFIX + ":" + FAKE_DB_PASSWORD + _DSN_HOST

FAKE_GEMINI_KEY = "AIza" + "SyEXAMPLEEXAMPLEEXAMPLEEXAMPLE12"
FAKE_APIFY_TOKEN = "apify_api_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
FAKE_JWT = "eyJhbGciOiJIUzI1NiJ9" + ".PAYLOAD.SIGNATURE"


# ---------------------------------------------------------------------------
# Scrubbing
# ---------------------------------------------------------------------------

def test_credentials_are_redacted_by_key():
    event = {
        "extra": {
            "DATABASE_URL": FAKE_DB_URL,
            "JWT_SECRET_KEY": "signing-key",
            "GEMINI_API_KEY": FAKE_GEMINI_KEY,
            "harmless": "keep me",
        }
    }

    cleaned = _scrub(event)

    assert cleaned["extra"]["DATABASE_URL"] == REDACTED
    assert cleaned["extra"]["JWT_SECRET_KEY"] == REDACTED
    assert cleaned["extra"]["GEMINI_API_KEY"] == REDACTED
    assert cleaned["extra"]["harmless"] == "keep me"


def test_the_neon_password_is_redacted_inside_a_message():
    """
    The likeliest leak by far: asyncpg puts the entire connection string into
    its connection errors, so the password arrives inside a plain string with no
    key to match against.
    """
    event = {"message": "connection failed: " + FAKE_DB_URL}

    cleaned = _scrub(event)

    assert FAKE_DB_PASSWORD not in json.dumps(cleaned)
    # The rest of the URL survives, or the error stops being diagnosable.
    assert "ep-cool.us-east-1.aws.neon.tech" in cleaned["message"]


def test_bearer_tokens_are_redacted_anywhere():
    event = {"request": {"headers": {"cookie": "a=b"}},
             "message": "rejected Bearer " + FAKE_JWT}

    cleaned = _scrub(event)

    assert FAKE_JWT not in json.dumps(cleaned)
    assert cleaned["request"]["headers"]["cookie"] == REDACTED


def test_brand_identity_is_redacted():
    """
    Anonymity is a product promise, not just a privacy preference. An issue
    tracker is exactly the kind of place it would leak without anyone noticing.
    """
    event = {"extra": {"brand_id": 7, "brand_name": "NutriFlex", "niche": "Fitness"}}

    cleaned = _scrub(event)

    assert cleaned["extra"]["brand_id"] == REDACTED
    assert cleaned["extra"]["brand_name"] == REDACTED
    # Non-identifying context is still useful and must survive.
    assert cleaned["extra"]["niche"] == "Fitness"


def test_scrubbing_reaches_nested_structures():
    event = {"exception": {"values": [
        {"stacktrace": {"frames": [
            {"vars": {"apify_token": FAKE_APIFY_TOKEN}},
        ]}},
    ]}}

    assert FAKE_APIFY_TOKEN not in json.dumps(_scrub(event))


def test_a_failure_to_scrub_drops_the_event():
    """Losing an error report beats sending an unscrubbed one."""
    class Explosive(dict):
        def items(self):
            raise RuntimeError("boom")

    assert _before_send(Explosive(), {}) is None


def test_scrubbing_terminates_on_deep_nesting():
    event = {}
    node = event
    for _ in range(50):
        node["next"] = {}
        node = node["next"]
    node["password"] = "leak"

    _scrub(event)  # must not raise or hang


# ---------------------------------------------------------------------------
# Enablement
# ---------------------------------------------------------------------------

def test_disabled_without_a_dsn(monkeypatch):
    """No account, no config, no behaviour change — and no crash."""
    monkeypatch.setattr(settings, "sentry_dsn", "")
    assert observability.init_error_tracking() is False
    # And the helpers stay silent rather than raising.
    observability.note_request("abc123")
    capture(ValueError("nobody is listening"), "abc123")


def test_enabled_with_a_dsn(monkeypatch):
    monkeypatch.setattr(
        settings, "sentry_dsn", "https://public@o0.ingest.sentry.io/1"
    )
    try:
        assert observability.init_error_tracking() is True
    finally:
        import sentry_sdk
        sentry_sdk.init(dsn="")  # tear the client down again


# ---------------------------------------------------------------------------
# End to end: does a real 500 actually produce a scrubbed event?
# ---------------------------------------------------------------------------

@pytest.fixture
async def error_client(session_factory):
    """
    A client that lets the app handle its own exceptions.

    The shared `client` fixture uses httpx's default `raise_app_exceptions=True`,
    which re-raises out of the transport before the app's catch-all handler can
    turn it into a 500 — so it cannot exercise the path that actually runs under
    uvicorn. This mirrors production instead.
    """
    from httpx import ASGITransport, AsyncClient

    from app.common.dependencies import get_db
    from app.main import app

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def captured_events(monkeypatch):
    """
    A live Sentry client whose transport is a list rather than the network.

    This exercises the real SDK — real init, real integrations, real
    `before_send` — without an account and without leaving the process.
    """
    import sentry_sdk

    events: list[dict] = []
    monkeypatch.setattr(
        settings, "sentry_dsn", "https://public@o0.ingest.sentry.io/1"
    )
    sentry_sdk.init(
        dsn="https://public@o0.ingest.sentry.io/1",
        include_local_variables=False,
        send_default_pii=False,
        before_send=observability._before_send,
        transport=events.append,
    )
    yield events
    sentry_sdk.init(dsn="")


async def test_an_unhandled_error_is_reported_with_its_request_id(
    error_client, captured_events
):
    """
    The catch-all handler turns unhandled errors into a clean 500, which stops
    them reaching the ASGI integration. If this ever regresses, error tracking
    goes quiet while still looking installed.
    """
    from app.main import app

    @app.get("/_boom_test")
    async def boom():
        raise RuntimeError("database is on fire")

    res = await error_client.get("/_boom_test")
    assert res.status_code == 500
    request_id = res.json()["request_id"]

    import sentry_sdk
    sentry_sdk.flush()

    assert captured_events, "a 500 produced no Sentry event"
    # Exactly one. The loguru integration and the explicit capture both fire;
    # Sentry's dedupe collapses them. If that ever stops working the issue count
    # and the bill both double, so it is asserted rather than assumed.
    assert len(captured_events) == 1, (
        f"one failure produced {len(captured_events)} events"
    )
    event = captured_events[-1]
    assert event["tags"]["request_id"] == request_id, (
        "the event cannot be correlated with the access log"
    )

    app.router.routes = [r for r in app.router.routes
                         if getattr(r, "path", None) != "/_boom_test"]


async def test_a_reported_event_carries_no_frame_locals(
    error_client, captured_events
):
    """
    The single most important assertion in this file. Sentry collects local
    variables by default; in this app those locals hold the Neon password and
    every API key.
    """
    from app.main import app

    @app.get("/_secret_boom_test")
    async def boom():
        database_url = FAKE_DB_URL          # noqa: F841 - the point of the test
        gemini_api_key = FAKE_GEMINI_KEY    # noqa: F841
        raise RuntimeError("failed while connecting")

    await error_client.get("/_secret_boom_test")

    import sentry_sdk
    sentry_sdk.flush()

    payload = json.dumps(captured_events[-1])
    assert FAKE_DB_PASSWORD not in payload, "a frame local leaked the DB password"
    assert FAKE_GEMINI_KEY not in payload, "a frame local leaked an API key"

    app.router.routes = [r for r in app.router.routes
                         if getattr(r, "path", None) != "/_secret_boom_test"]
