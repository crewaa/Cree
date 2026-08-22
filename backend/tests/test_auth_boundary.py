"""
Tests for the authentication boundary.

These cover the findings from docs/07-risks-and-gaps.md §4: setup tokens being
usable as access tokens, `is_active` never being enforced, and the missing
guard on set-password. Each test fails against the pre-hardening code.
"""

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token
from app.modules.auth.service import create_setup_token
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio


async def test_setup_token_is_rejected_as_a_session_credential(client, session_factory):
    """
    A setup token authorises exactly one action: setting a password. It is
    signed with the same secret as an access token, so it must be rejected
    explicitly rather than by accident.
    """
    await make_user(session_factory, "google@example.com", "INFLUENCER", password=None)
    setup_token = create_setup_token("google@example.com", "INFLUENCER")

    res = await client.get("/users/me", headers={"Authorization": f"Bearer {setup_token}"})

    assert res.status_code == 401
    assert "cannot be used for authentication" in res.json()["detail"]


async def test_setup_token_forged_with_a_sub_claim_is_still_rejected(client, session_factory):
    """
    Defence in depth: even if a setup token gained a `sub` claim, the `purpose`
    claim must still disqualify it. Without this the token becomes a full
    session for an account that has not yet been secured.
    """
    user = await make_user(session_factory, "victim@example.com", "ADMIN")
    forged = jwt.encode(
        {"purpose": "set_password", "sub": str(user.id), "role": "ADMIN"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    res = await client.get("/users/me", headers={"Authorization": f"Bearer {forged}"})

    assert res.status_code == 401


async def test_access_token_carries_an_explicit_type_claim():
    payload = jwt.decode(
        create_access_token({"sub": "1", "role": "BRAND"}, 60),
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["type"] == "access"


async def test_deactivated_user_loses_access(client, session_factory):
    """`is_active` was stored and shown in the admin UI but never enforced."""
    user = await make_user(session_factory, "banned@example.com", "BRAND", is_active=False)

    res = await client.get("/users/me", headers=auth_header(user))

    assert res.status_code == 403
    assert "disabled" in res.json()["detail"].lower()


async def test_deactivated_user_cannot_log_in(client, session_factory):
    await make_user(session_factory, "banned2@example.com", "BRAND", is_active=False)

    res = await client.post(
        "/auth/login",
        json={"email": "banned2@example.com", "password": "correct-horse-battery"},
    )

    assert res.status_code == 403


async def test_set_password_cannot_overwrite_an_existing_password(client, session_factory):
    """
    A replayed setup token must not become a password reset for an account that
    is already secured.
    """
    await make_user(session_factory, "secured@example.com", "BRAND", password="original-password")
    setup_token = create_setup_token("secured@example.com", "BRAND")

    res = await client.post(
        "/auth/set-password",
        json={"setup_token": setup_token, "password": "attacker-chosen-pw"},
    )

    assert res.status_code == 400
    assert "already has a password" in res.json()["detail"]

    # The original password still works.
    login = await client.post(
        "/auth/login",
        json={"email": "secured@example.com", "password": "original-password"},
    )
    assert login.status_code == 200


async def test_set_password_completes_a_google_only_account(client, session_factory):
    await make_user(session_factory, "newgoogle@example.com", "INFLUENCER", password=None)
    setup_token = create_setup_token("newgoogle@example.com", "INFLUENCER")

    res = await client.post(
        "/auth/set-password",
        json={"setup_token": setup_token, "password": "a-strong-password"},
    )

    assert res.status_code == 200
    assert res.json()["role"] == "INFLUENCER"


@pytest.mark.parametrize("token", ["", "not.a.jwt", "a.b.c"])
async def test_malformed_tokens_are_rejected(client, token):
    res = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


async def test_missing_token_is_rejected(client):
    assert (await client.get("/users/me")).status_code == 401


async def test_signup_rejects_weak_passwords(client):
    res = await client.post(
        "/auth/signup",
        json={"email": "weak@example.com", "password": "short", "role": "BRAND"},
    )
    assert res.status_code == 400
    assert "at least" in res.json()["detail"]


async def test_signup_cannot_create_an_admin(client):
    res = await client.post(
        "/auth/signup",
        json={"email": "sneaky@example.com", "password": "a-strong-password", "role": "ADMIN"},
    )
    assert res.status_code == 403


async def test_signup_then_login_round_trip(client):
    signup = await client.post(
        "/auth/signup",
        json={"email": "fresh@example.com", "password": "a-strong-password", "role": "INFLUENCER"},
    )
    assert signup.status_code == 200
    assert signup.json()["role"] == "INFLUENCER"

    me = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {signup.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "fresh@example.com"
