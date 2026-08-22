"""
Tests for rate limiting.

The credential endpoints were previously an unbounded password-guessing oracle,
and the scrape/AI endpoints could be called without limit despite each call
costing money or third-party quota.
"""

import pytest

from app.common.rate_limit import _Counter
from tests.conftest import auth_header, make_user


def test_counter_allows_up_to_the_limit_then_blocks():
    counter = _Counter()

    for _ in range(3):
        allowed, _ = counter.hit("k", limit=3, window_seconds=60)
        assert allowed

    allowed, retry_after = counter.hit("k", limit=3, window_seconds=60)
    assert not allowed
    assert retry_after > 0


def test_counter_keys_are_independent():
    counter = _Counter()

    for _ in range(3):
        counter.hit("user-a", limit=3, window_seconds=60)

    allowed, _ = counter.hit("user-b", limit=3, window_seconds=60)
    assert allowed, "one client's usage must not throttle another"


def test_counter_window_expires():
    counter = _Counter()

    # A zero-length window means every previous hit is already outside it.
    for _ in range(10):
        allowed, _ = counter.hit("k", limit=1, window_seconds=0)
        assert allowed


async def test_repeated_failed_logins_are_throttled(client, session_factory):
    await make_user(session_factory, "target@example.com", "BRAND", password="the-real-password")

    statuses = []
    for _ in range(15):
        res = await client.post(
            "/auth/login",
            json={"email": "target@example.com", "password": "wrong-guess"},
        )
        statuses.append(res.status_code)

    assert 429 in statuses, "brute-force attempts must eventually be blocked"
    assert statuses.index(429) <= 11, "the limit should engage promptly"


async def test_rate_limited_response_includes_retry_after(client, session_factory):
    await make_user(session_factory, "target2@example.com", "BRAND")

    last = None
    for _ in range(15):
        last = await client.post(
            "/auth/login",
            json={"email": "target2@example.com", "password": "wrong"},
        )
        if last.status_code == 429:
            break

    assert last.status_code == 429
    assert "retry-after" in {k.lower() for k in last.headers}


async def test_scrape_endpoint_is_throttled_per_user(client, session_factory):
    """Each scrape spends Apify credit, so the cap is per account, not per IP."""
    user = await make_user(session_factory, "spender@example.com", "INFLUENCER")

    statuses = []
    for _ in range(10):
        res = await client.post(
            f"/instagram/scrape/{user.id}", headers=auth_header(user)
        )
        statuses.append(res.status_code)

    assert 429 in statuses


async def test_throttling_one_user_does_not_affect_another(client, session_factory):
    heavy = await make_user(session_factory, "heavy@example.com", "INFLUENCER")
    light = await make_user(session_factory, "light@example.com", "INFLUENCER")

    for _ in range(10):
        await client.post(f"/instagram/scrape/{heavy.id}", headers=auth_header(heavy))

    res = await client.post(f"/instagram/scrape/{light.id}", headers=auth_header(light))
    assert res.status_code == 200
