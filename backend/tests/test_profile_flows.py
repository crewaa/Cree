"""
Tests for the creator/brand profile flows.

Includes the server-side auto-scrape behaviour that the frontend now relies on:
the wrongly-targeted client-side scrape calls were deleted (they passed
creator_profiles.id where users.id was expected), so the backend queueing the
job correctly is now the only path.
"""

import json

import pytest

from tests.conftest import auth_header, make_brand_profile, make_creator_profile, make_user


async def test_creating_a_profile_queues_scrapes_for_both_platforms(
    client, session_factory, monkeypatch
):
    user = await make_user(session_factory, "creator@example.com", "INFLUENCER")

    queued: list[tuple[str, int]] = []

    async def fake_ig(user_id):
        queued.append(("instagram", user_id))

    async def fake_yt(user_id):
        queued.append(("youtube", user_id))

    monkeypatch.setattr("app.modules.users.router.scrape_and_store", fake_ig)
    monkeypatch.setattr("app.modules.users.router.scrape_and_store_youtube", fake_yt)

    res = await client.post(
        "/users/creator-profile",
        json={
            "full_name": "Creator", "location": "Mumbai",
            "primary_platform": "Instagram", "category": "Fitness",
            "instagram_username": "insta_handle", "youtube_username": "yt_handle",
        },
        headers=auth_header(user),
    )

    assert res.status_code == 200
    # Critically, the queued id is users.id — not the new creator_profiles.id.
    assert ("instagram", user.id) in queued
    assert ("youtube", user.id) in queued


async def test_no_scrape_is_queued_without_a_username(
    client, session_factory, monkeypatch
):
    user = await make_user(session_factory, "nohandles@example.com", "INFLUENCER")

    queued = []

    async def fake_ig(user_id):
        queued.append(user_id)

    monkeypatch.setattr("app.modules.users.router.scrape_and_store", fake_ig)

    res = await client.post(
        "/users/creator-profile",
        json={
            "full_name": "Creator", "location": "Delhi",
            "primary_platform": "Instagram", "category": "Food",
        },
        headers=auth_header(user),
    )

    assert res.status_code == 200
    assert queued == []


async def test_profile_cannot_be_created_twice(client, session_factory):
    user = await make_user(session_factory, "dup@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, user.id)

    res = await client.post(
        "/users/creator-profile",
        json={
            "full_name": "Again", "location": "Pune",
            "primary_platform": "Instagram", "category": "Tech",
        },
        headers=auth_header(user),
    )

    assert res.status_code == 400


async def test_updating_a_profile_persists_changes(client, session_factory):
    user = await make_user(session_factory, "upd@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, user.id, full_name="Old Name")

    res = await client.put(
        "/users/creator-profile",
        json={
            "full_name": "New Name", "location": "Goa",
            "primary_platform": "YouTube", "category": "Travel",
        },
        headers=auth_header(user),
    )

    assert res.status_code == 200
    assert res.json()["full_name"] == "New Name"

    fetched = await client.get("/users/creator-profile", headers=auth_header(user))
    assert fetched.json()["full_name"] == "New Name"


async def test_missing_profile_returns_404(client, session_factory):
    user = await make_user(session_factory, "noprofile@example.com", "INFLUENCER")
    res = await client.get("/users/creator-profile", headers=auth_header(user))
    assert res.status_code == 404


async def test_brand_profile_round_trip(client, session_factory):
    brand = await make_user(session_factory, "brand@example.com", "BRAND")

    created = await client.post(
        "/users/brand-profile",
        json={
            "brand_name": "Acme", "industry": "Fitness",
            "campaign_goal": "Sales", "budget_range": "High",
            "target_languages": json.dumps(["English", "Hindi"]),
        },
        headers=auth_header(brand),
    )

    assert created.status_code == 200
    assert created.json()["campaign_goal"] == "Sales"

    fetched = await client.get("/users/brand-profile", headers=auth_header(brand))
    assert json.loads(fetched.json()["target_languages"]) == ["English", "Hindi"]


async def test_saved_creators_only_returns_the_callers_rows(client, session_factory):
    from app.modules.users.models import SavedCreator

    brand_a = await make_user(session_factory, "ba@example.com", "BRAND")
    brand_b = await make_user(session_factory, "bb@example.com", "BRAND")
    creator = await make_user(session_factory, "cc@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, full_name="Shared Creator")

    async with session_factory() as db:
        db.add(SavedCreator(
            brand_id=brand_a.id, creator_id=creator.id,
            fit_level="High", score_reasoning=json.dumps(["good match"]),
        ))
        await db.commit()

    res_a = await client.get("/users/saved-creators", headers=auth_header(brand_a))
    assert res_a.status_code == 200
    assert len(res_a.json()) == 1
    assert res_a.json()[0]["creator_name"] == "Shared Creator"

    res_b = await client.get("/users/saved-creators", headers=auth_header(brand_b))
    assert res_b.json() == []


async def test_deleting_a_user_cascades_their_data(client, session_factory):
    from sqlalchemy import select
    from app.modules.users.models import CreatorProfile

    admin = await make_user(session_factory, "admin@example.com", "ADMIN")
    creator = await make_user(session_factory, "doomed@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id)

    res = await client.delete(f"/admin/users/{creator.id}", headers=auth_header(admin))
    assert res.status_code == 200

    async with session_factory() as db:
        profile = (await db.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == creator.id)
        )).scalar()

    assert profile is None, "creator_profiles row should cascade with the user"


async def test_health_check_reports_database_status(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


async def test_every_response_carries_a_request_id(client):
    res = await client.get("/health")
    assert res.headers.get("X-Request-ID")
