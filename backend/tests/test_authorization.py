"""
Tests for authorization: role guards and resource ownership.

Covers docs/07-risks-and-gaps.md §3 — the endpoints that previously took no
authentication dependency at all, including the one that let any anonymous
caller overwrite any creator's profile.
"""

import pytest
from fastapi.routing import APIRoute

from app.main import app
from tests.conftest import auth_header, make_brand_profile, make_creator_profile, make_user

# asyncio_mode=auto in pytest.ini handles the async tests; the two
# route-introspection tests below are deliberately synchronous.


PUBLIC_PATHS = {
    "/auth/signup", "/auth/login", "/auth/google", "/auth/set-password",
    "/auth/logout", "/health",
}


def _all_api_routes():
    """Flatten the route tree; newer FastAPI nests included routers."""
    found, stack = [], list(app.routes)
    while stack:
        route = stack.pop()
        if hasattr(route, "dependant"):
            found.append(route)
        elif hasattr(route, "original_router"):
            stack.extend(route.original_router.routes)
        elif hasattr(route, "routes"):
            stack.extend(route.routes)
    return found


def test_no_endpoint_is_unintentionally_public():
    """
    Regression guard for the original finding. If someone adds a route without
    an auth dependency, this fails and names it.
    """
    guards = {
        "get_current_user",
        "require_self_or_admin",
        "require_admin",
        "_role_checker",
    }
    # NB: deliberately excludes the rate-limiter closures. A throttle is not an
    # authentication guard, and counting it as one would hide an open endpoint.
    unprotected = []

    for route in _all_api_routes():
        if not isinstance(route, APIRoute) or route.path in PUBLIC_PATHS:
            continue

        names, stack = set(), [route.dependant]
        while stack:
            dep = stack.pop()
            if dep.call is not None:
                names.add(getattr(dep.call, "__name__", ""))
            stack.extend(dep.dependencies)

        if not (names & guards):
            unprotected.append(f"{sorted(route.methods)} {route.path}")

    assert not unprotected, f"Endpoints missing an auth dependency: {unprotected}"


def test_removed_creator_profile_by_id_routes_are_gone():
    """
    `PUT /users/creator-profile/{user_id}` was unauthenticated and allowed
    overwriting anyone's profile. It must not come back.
    """
    paths = {r.path for r in _all_api_routes() if isinstance(r, APIRoute)}
    assert "/users/creator-profile/{user_id}" not in paths


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

async def test_user_cannot_read_another_users_instagram_analytics(client, session_factory):
    victim = await make_user(session_factory, "victim@example.com", "INFLUENCER")
    attacker = await make_user(session_factory, "attacker@example.com", "INFLUENCER")

    res = await client.get(
        f"/instagram/analytics/{victim.id}", headers=auth_header(attacker)
    )

    assert res.status_code == 403


async def test_user_cannot_trigger_a_scrape_for_another_user(client, session_factory):
    """Scrapes cost money, so this is an abuse vector as well as a privacy one."""
    victim = await make_user(session_factory, "victim2@example.com", "INFLUENCER")
    attacker = await make_user(session_factory, "attacker2@example.com", "INFLUENCER")

    res = await client.post(
        f"/instagram/scrape/{victim.id}", headers=auth_header(attacker)
    )

    assert res.status_code == 403


async def test_user_cannot_read_another_users_youtube_analytics(client, session_factory):
    victim = await make_user(session_factory, "victim3@example.com", "INFLUENCER")
    attacker = await make_user(session_factory, "attacker3@example.com", "INFLUENCER")

    res = await client.get(
        f"/youtube/analytics/{victim.id}", headers=auth_header(attacker)
    )

    assert res.status_code == 403


async def test_user_can_read_their_own_analytics(client, session_factory):
    user = await make_user(session_factory, "self@example.com", "INFLUENCER")

    res = await client.get(f"/instagram/analytics/{user.id}", headers=auth_header(user))

    assert res.status_code == 200
    assert res.json()["status"] == "no_data"


async def test_admin_can_read_any_users_analytics(client, session_factory):
    creator = await make_user(session_factory, "creator@example.com", "INFLUENCER")
    admin = await make_user(session_factory, "admin@example.com", "ADMIN")

    res = await client.get(
        f"/instagram/analytics/{creator.id}", headers=auth_header(admin)
    )

    assert res.status_code == 200


async def test_unauthenticated_scrape_is_rejected(client, session_factory):
    user = await make_user(session_factory, "someone@example.com", "INFLUENCER")
    assert (await client.post(f"/instagram/scrape/{user.id}")).status_code == 401


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------

async def test_influencer_cannot_use_brand_discovery(client, session_factory):
    creator = await make_user(session_factory, "c@example.com", "INFLUENCER")

    res = await client.post(
        "/ai/discover-creators",
        json={"niche": "Fitness"},
        headers=auth_header(creator),
    )

    assert res.status_code == 403


async def test_brand_cannot_read_creator_brand_deals(client, session_factory):
    brand = await make_user(session_factory, "b@example.com", "BRAND")

    res = await client.get("/ai/brand-deals", headers=auth_header(brand))

    assert res.status_code == 403


async def test_non_admin_cannot_reach_admin_endpoints(client, session_factory):
    brand = await make_user(session_factory, "b2@example.com", "BRAND")

    assert (await client.get("/admin/stats", headers=auth_header(brand))).status_code == 403
    assert (await client.get("/admin/users", headers=auth_header(brand))).status_code == 403


async def test_admin_stats_counts_by_role(client, session_factory):
    admin = await make_user(session_factory, "admin2@example.com", "ADMIN")
    await make_user(session_factory, "c1@example.com", "INFLUENCER")
    await make_user(session_factory, "c2@example.com", "INFLUENCER")
    await make_user(session_factory, "b1@example.com", "BRAND")

    res = await client.get("/admin/stats", headers=auth_header(admin))

    assert res.status_code == 200
    body = res.json()
    assert body["total_creators"] == 2
    assert body["total_brands"] == 1
    assert body["total_admins"] == 1


async def test_admin_cannot_delete_another_admin(client, session_factory):
    admin = await make_user(session_factory, "admin3@example.com", "ADMIN")
    other = await make_user(session_factory, "admin4@example.com", "ADMIN")

    res = await client.delete(f"/admin/users/{other.id}", headers=auth_header(admin))

    assert res.status_code == 400


async def test_admin_user_list_pagination_is_clamped(client, session_factory):
    """page=0 previously produced a negative OFFSET and a database error."""
    admin = await make_user(session_factory, "admin5@example.com", "ADMIN")

    res = await client.get(
        "/admin/users?page=0&page_size=100000", headers=auth_header(admin)
    )

    assert res.status_code == 200
    assert res.json()["page"] == 1
    assert res.json()["page_size"] <= 100


# ---------------------------------------------------------------------------
# Profile ownership
# ---------------------------------------------------------------------------

async def test_creator_profile_is_scoped_to_the_caller(client, session_factory):
    a = await make_user(session_factory, "a@example.com", "INFLUENCER")
    b = await make_user(session_factory, "b3@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, a.id, full_name="Creator A")
    await make_creator_profile(session_factory, b.id, full_name="Creator B")

    res = await client.get("/users/creator-profile", headers=auth_header(b))

    assert res.status_code == 200
    assert res.json()["full_name"] == "Creator B"


async def test_brand_profile_is_scoped_to_the_caller(client, session_factory):
    a = await make_user(session_factory, "ba@example.com", "BRAND")
    b = await make_user(session_factory, "bb@example.com", "BRAND")
    await make_brand_profile(session_factory, a.id, brand_name="Brand A")
    await make_brand_profile(session_factory, b.id, brand_name="Brand B")

    res = await client.get("/users/brand-profile", headers=auth_header(b))

    assert res.status_code == 200
    assert res.json()["brand_name"] == "Brand B"


async def test_brand_cannot_access_creator_profile_endpoint(client, session_factory):
    brand = await make_user(session_factory, "brandx@example.com", "BRAND")
    assert (await client.get("/users/creator-profile", headers=auth_header(brand))).status_code == 403
