"""
Tests for the sign-in and sign-up problems reported as
"sometimes it works, sometimes it doesn't, and it's slow".

Each test below corresponds to a cause that was reproduced before it was fixed,
so this file doubles as the record of what was actually wrong:

1. bcrypt ran on the event loop, so one sign-in froze the whole worker.
2. `Vishal@gmail.com` and `vishal@gmail.com` were different accounts.
3. Two simultaneous sign-ups for one address returned HTTP 500.
4. The login throttle counted successes, so a correct password could be refused.
5. Sign-up hashed the password, then verified it again — twice the slowest work
   in the request, for no extra certainty.
6. A missing account answered in ~1ms and a wrong password in ~180ms, which
   tells an attacker which addresses have accounts.
"""

import asyncio
import time

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.modules.users.models import User
from tests.conftest import make_user

SIGNUP = {"email": "New.Person@Gmail.com", "password": "CrewaaTest123!", "role": "INFLUENCER"}


# ---------------------------------------------------------------------------
# 1. Email case
# ---------------------------------------------------------------------------

async def test_sign_in_works_whatever_case_the_email_is_typed_in(client):
    """
    The quietest of the failures: right password, "Invalid credentials", no
    explanation anywhere in the product.
    """
    await client.post("/auth/signup", json=SIGNUP)

    for typed in ["new.person@gmail.com", "New.Person@Gmail.com", "NEW.PERSON@GMAIL.COM",
                  "  new.person@gmail.com  "]:
        res = await client.post(
            "/auth/login", json={"email": typed.strip(), "password": SIGNUP["password"]}
        )
        assert res.status_code == 200, f"could not sign in with {typed!r}"


async def test_a_second_account_cannot_be_made_by_changing_the_case(client, session_factory):
    await client.post("/auth/signup", json=SIGNUP)

    res = await client.post(
        "/auth/signup", json={**SIGNUP, "email": "new.person@gmail.com", "role": "BRAND"}
    )

    assert res.status_code == 400
    async with session_factory() as db:
        count = (await db.execute(
            select(func.count()).select_from(User)
            .where(func.lower(User.email) == "new.person@gmail.com")
        )).scalar()
    assert count == 1, "the same person now has two accounts"


async def test_the_stored_address_is_normalised(client, session_factory):
    await client.post("/auth/signup", json=SIGNUP)

    async with session_factory() as db:
        stored = (await db.execute(select(User.email))).scalars().first()

    assert stored == "new.person@gmail.com"


async def test_an_account_created_before_normalisation_can_still_sign_in(
    client, session_factory
):
    """
    Existing rows keep their original casing. Lookup is case-insensitive
    precisely so those users are not locked out by this change.
    """
    await make_user(session_factory, "Legacy.User@Gmail.com", "INFLUENCER")
    async with session_factory() as db:
        user = (await db.execute(select(User))).scalars().first()
        user.hashed_password = hash_password("CrewaaTest123!")
        await db.commit()

    res = await client.post(
        "/auth/login",
        json={"email": "legacy.user@gmail.com", "password": "CrewaaTest123!"},
    )

    assert res.status_code == 200


# ---------------------------------------------------------------------------
# 2. Concurrent signup
# ---------------------------------------------------------------------------

async def test_simultaneous_signups_never_return_a_server_error(client, session_factory):
    """
    A double submit, a retried request or two open tabs used to produce a 500 —
    for every request, including the one that should have succeeded.
    """
    responses = await asyncio.gather(*[
        client.post("/auth/signup", json=SIGNUP) for _ in range(5)
    ])
    codes = [r.status_code for r in responses]

    assert 500 not in codes, f"race still produces a server error: {codes}"
    assert codes.count(200) <= 1, "more than one account was created"
    assert all(c in (200, 400) for c in codes), codes

    async with session_factory() as db:
        count = (await db.execute(select(func.count()).select_from(User))).scalar()
    assert count <= 1


async def test_a_losing_signup_is_not_handed_the_winners_account(client, session_factory):
    """
    Caught while fixing the 500 above, and worse than the bug it replaced.

    Re-reading the row after a lost race is right; *returning* it is not. Two
    people racing to register the same address would both receive a token, and
    the loser would hold a valid session for an account whose password they
    never chose. Success is only reported when the row that exists is the one
    this request inserted.
    """
    responses = await asyncio.gather(*[
        client.post("/auth/signup", json=SIGNUP) for _ in range(5)
    ])

    tokens = [
        r.json()["access_token"] for r in responses
        if r.status_code == 200 and "access_token" in r.json()
    ]

    assert len(tokens) <= 1, (
        f"{len(tokens)} sign-ups were given a session for one account"
    )

    async with session_factory() as db:
        accounts = (await db.execute(select(func.count()).select_from(User))).scalar()
    assert accounts == 1


async def test_a_duplicate_signup_explains_what_to_do(client):
    await client.post("/auth/signup", json=SIGNUP)
    res = await client.post("/auth/signup", json=SIGNUP)

    assert res.status_code == 400
    assert "log in" in res.json()["detail"].lower(), (
        "the error should tell the person what to do next"
    )


# ---------------------------------------------------------------------------
# 3. Lockout counts failures, not attempts
# ---------------------------------------------------------------------------

async def test_a_correct_password_is_never_refused_for_rate_limiting(client):
    """
    The regression that made the product feel broken: several wrong attempts,
    then the right one, answered with "Too many requests".
    """
    await client.post("/auth/signup", json=SIGNUP)

    for _ in range(settings.login_max_failures - 1):
        bad = await client.post(
            "/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"}
        )
        assert bad.status_code == 401

    good = await client.post(
        "/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]}
    )

    assert good.status_code == 200, "a correct password was refused as rate limiting"


async def test_a_successful_sign_in_clears_the_failure_count(client):
    """Otherwise yesterday's typos still count against you today."""
    await client.post("/auth/signup", json=SIGNUP)

    for _ in range(settings.login_max_failures - 1):
        await client.post(
            "/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"}
        )
    await client.post(
        "/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]}
    )

    # The counter is back to zero, so there is room to fail again.
    again = await client.post(
        "/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"}
    )
    assert again.status_code == 401, "failures were not cleared by a successful sign-in"


async def test_persistent_guessing_is_still_locked_out(client):
    """The protection has to survive being made friendlier."""
    await client.post("/auth/signup", json=SIGNUP)

    codes = []
    for _ in range(settings.login_max_failures + 3):
        res = await client.post(
            "/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"}
        )
        codes.append(res.status_code)

    assert 429 in codes, "brute-force guessing is no longer throttled"


async def test_the_lockout_message_says_how_long(client):
    await client.post("/auth/signup", json=SIGNUP)
    for _ in range(settings.login_max_failures + 1):
        res = await client.post(
            "/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"}
        )

    detail = res.json()["detail"]
    assert "minute" in detail, f"unhelpful lockout message: {detail!r}"
    assert res.headers.get("Retry-After")


async def test_one_persons_failures_do_not_lock_out_another(client):
    """Keyed on email+IP, so guessing at one account cannot deny service to all."""
    await client.post("/auth/signup", json=SIGNUP)
    await client.post("/auth/signup", json={**SIGNUP, "email": "other@gmail.com"})

    for _ in range(settings.login_max_failures + 2):
        await client.post(
            "/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"}
        )

    res = await client.post(
        "/auth/login", json={"email": "other@gmail.com", "password": SIGNUP["password"]}
    )
    assert res.status_code == 200, "an unrelated account was locked out"


# ---------------------------------------------------------------------------
# 4. Cost and concurrency
# ---------------------------------------------------------------------------

async def test_signup_hashes_the_password_only_once(client, monkeypatch):
    """
    Sign-up used to hash the password and then verify it again to mint a token,
    paying for the slowest operation in the request twice.
    """
    from app.core import security

    calls = {"hash": 0, "verify": 0}
    real_hash, real_verify = security.pwd_context.hash, security.pwd_context.verify

    def counted_hash(pw):
        calls["hash"] += 1
        return real_hash(pw)

    def counted_verify(pw, h):
        calls["verify"] += 1
        return real_verify(pw, h)

    monkeypatch.setattr(security.pwd_context, "hash", counted_hash)
    monkeypatch.setattr(security.pwd_context, "verify", counted_verify)

    res = await client.post("/auth/signup", json=SIGNUP)

    assert res.status_code == 200
    assert calls["hash"] == 1, f"hashed {calls['hash']} times"
    assert calls["verify"] == 0, "sign-up is still verifying a password it just set"


async def test_password_hashing_does_not_block_the_event_loop():
    """
    The cause of "slow when more than one person is using it". bcrypt is
    CPU-bound and ~180ms; run inline it freezes every other request on the
    worker for that whole time.
    """
    from app.core.security import hash_password_async

    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.005)
            ticks += 1

    beat = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.02)
    ticks = 0

    await hash_password_async("CrewaaTest123!")
    beat.cancel()

    assert ticks > 0, "the event loop was blocked for the whole hash"


async def test_concurrent_sign_ins_overlap(client):
    """
    Five sign-ins should take roughly as long as the slowest, not the sum. This
    asserts the shape rather than a wall-clock number, so it does not turn into
    a flaky test on a loaded CI machine.
    """
    await client.post("/auth/signup", json=SIGNUP)
    payload = {"email": SIGNUP["email"], "password": SIGNUP["password"]}

    start = time.perf_counter()
    await client.post("/auth/login", json=payload)
    one = time.perf_counter() - start

    start = time.perf_counter()
    await asyncio.gather(*[client.post("/auth/login", json=payload) for _ in range(5)])
    five = time.perf_counter() - start

    assert five < one * 4, (
        f"five sign-ins took {five:.2f}s against {one:.2f}s for one — "
        "they are still running one at a time"
    )


# ---------------------------------------------------------------------------
# 5. Account enumeration
# ---------------------------------------------------------------------------

async def test_a_missing_account_costs_the_same_as_a_wrong_password(client):
    """
    Returning instantly for an unknown address leaks which emails are
    registered. The gap was ~1ms versus ~180ms, which is trivially measurable
    over the network.
    """
    await client.post("/auth/signup", json=SIGNUP)

    start = time.perf_counter()
    await client.post("/auth/login",
                      json={"email": SIGNUP["email"], "password": "wrong-password"})
    known = time.perf_counter() - start

    start = time.perf_counter()
    await client.post("/auth/login",
                      json={"email": "nobody@gmail.com", "password": "wrong-password"})
    unknown = time.perf_counter() - start

    # Generous bound: the point is that one is not orders of magnitude faster.
    assert unknown > known * 0.4, (
        f"unknown account answered in {unknown*1000:.0f}ms vs {known*1000:.0f}ms "
        "for a known one — that difference identifies registered users"
    )


async def test_the_sign_in_error_does_not_say_which_half_was_wrong(client):
    await client.post("/auth/signup", json=SIGNUP)

    missing = await client.post(
        "/auth/login", json={"email": "nobody@gmail.com", "password": "x" * 12})
    wrong = await client.post(
        "/auth/login", json={"email": SIGNUP["email"], "password": "x" * 12})

    assert missing.json()["detail"] == wrong.json()["detail"]
