"""
Tests for the scraping layer.

Covers the field mappers (which parse third-party payload shapes we do not
control), the scrape-job bookkeeping that makes failures visible, and the
cross-account YouTube channel bug from docs/07-risks-and-gaps.md §6.
"""

import pytest
from sqlalchemy import select

from app.modules.instagram.scrapper.scrapper import scrape_instagram
from app.modules.scraping.models import ScrapeJob, ScrapePlatform, ScrapeStatus
from app.modules.youtube.scrapper import parse_duration
from tests.conftest import auth_header, make_creator_profile, make_user


# ---------------------------------------------------------------------------
# YouTube ISO-8601 duration parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "iso,seconds",
    [
        ("PT1H23M45S", 5025),
        ("PT10M", 600),
        ("PT45S", 45),
        ("PT2H", 7200),
        ("PT0S", 0),
        ("", 0),          # malformed input must not raise
        ("garbage", 0),
    ],
)
def test_parse_duration(iso, seconds):
    assert parse_duration(iso) == seconds


# ---------------------------------------------------------------------------
# Instagram field mapping
# ---------------------------------------------------------------------------

async def test_instagram_mapper_handles_the_documented_apify_shape(monkeypatch):
    async def fake_apify(username):
        return {
            "username": "creator",
            "fullName": "A Creator",
            "biography": "bio text",
            "profilePicUrl": "https://example.com/pic.jpg",
            "followersCount": 1000,
            "followsCount": 200,
            "postsCount": 50,
            "verified": True,
            "latestPosts": [
                {
                    "shortCode": "abc",
                    "likesCount": 100,
                    "commentsCount": 10,
                    "type": "Video",
                    "videoViewCount": 5000,
                    "caption": "hello",
                    "timestamp": "2026-01-01T00:00:00Z",
                }
            ],
        }

    monkeypatch.setattr(
        "app.modules.instagram.scrapper.scrapper.scrape_instagram_creator", fake_apify
    )

    result = await scrape_instagram("creator")

    assert result["profile"]["followers"] == 1000
    assert result["profile"]["is_verified"] is True
    assert len(result["posts"]) == 1
    assert result["posts"][0]["is_video"] is True
    assert result["posts"][0]["views"] == 5000


async def test_instagram_mapper_tolerates_missing_fields(monkeypatch):
    """Apify field names have changed before; absent keys must not crash."""
    async def fake_apify(username):
        return {"username": "sparse"}

    monkeypatch.setattr(
        "app.modules.instagram.scrapper.scrapper.scrape_instagram_creator", fake_apify
    )

    result = await scrape_instagram("sparse")

    assert result["profile"]["followers"] == 0
    assert result["profile"]["is_verified"] is False
    assert result["posts"] == []


async def test_instagram_mapper_skips_unparseable_posts(monkeypatch):
    async def fake_apify(username):
        return {
            "username": "creator",
            "latestPosts": [
                {"shortCode": "good", "likesCount": 5, "commentsCount": 1},
                {"shortCode": "bad", "likesCount": "not-a-number"},
            ],
        }

    monkeypatch.setattr(
        "app.modules.instagram.scrapper.scrapper.scrape_instagram_creator", fake_apify
    )

    result = await scrape_instagram("creator")

    assert [p["shortcode"] for p in result["posts"]] == ["good"]


# ---------------------------------------------------------------------------
# Scrape job bookkeeping
# ---------------------------------------------------------------------------

async def test_failed_scrape_records_a_readable_error(session_factory, monkeypatch):
    """
    Previously a failure was invisible: the task logged to stdout and the user
    saw an empty dashboard forever.
    """
    user = await make_user(session_factory, "creator@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, user.id, instagram_username="ghost")

    monkeypatch.setattr(
        "app.modules.instagram.services.instagram_scrapper.AsyncSessionLocal",
        session_factory,
    )

    async def boom(username):
        raise Exception("Apify actor failed")

    monkeypatch.setattr(
        "app.modules.instagram.services.instagram_scrapper.scrape_instagram", boom
    )

    from app.modules.instagram.services.instagram_scrapper import scrape_and_store

    result = await scrape_and_store(user.id)
    assert result["status"] == "error"

    async with session_factory() as db:
        job = (await db.execute(
            select(ScrapeJob).where(ScrapeJob.user_id == user.id)
        )).scalar()

    assert job is not None
    assert job.status == ScrapeStatus.ERROR
    assert job.platform == ScrapePlatform.INSTAGRAM
    assert "ghost" in job.message
    assert job.finished_at is not None
    # The user-facing message must not leak internal detail.
    assert "Apify actor failed" not in job.message


async def test_missing_username_is_reported_not_silently_dropped(
    session_factory, monkeypatch
):
    user = await make_user(session_factory, "nouser@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, user.id, instagram_username=None)

    monkeypatch.setattr(
        "app.modules.instagram.services.instagram_scrapper.AsyncSessionLocal",
        session_factory,
    )

    from app.modules.instagram.services.instagram_scrapper import scrape_and_store

    await scrape_and_store(user.id)

    async with session_factory() as db:
        job = (await db.execute(
            select(ScrapeJob).where(ScrapeJob.user_id == user.id)
        )).scalar()

    assert job.status == ScrapeStatus.ERROR
    assert "No Instagram username" in job.message


async def test_successful_scrape_is_recorded(session_factory, monkeypatch):
    user = await make_user(session_factory, "ok@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, user.id, instagram_username="good")

    monkeypatch.setattr(
        "app.modules.instagram.services.instagram_scrapper.AsyncSessionLocal",
        session_factory,
    )

    async def fake_scrape(username):
        return {
            "profile": {
                "username": username, "full_name": "N", "bio": "", "profile_picture": "",
                "followers": 10, "following": 5, "posts_count": 1, "is_verified": False,
            },
            "posts": [],
        }

    monkeypatch.setattr(
        "app.modules.instagram.services.instagram_scrapper.scrape_instagram", fake_scrape
    )

    from app.modules.instagram.services.instagram_scrapper import scrape_and_store

    result = await scrape_and_store(user.id)

    assert result["status"] == "success"

    async with session_factory() as db:
        job = (await db.execute(
            select(ScrapeJob).where(ScrapeJob.user_id == user.id)
        )).scalar()

    assert job.status == ScrapeStatus.SUCCESS


async def test_scrape_status_endpoint_reports_the_latest_attempt(
    client, session_factory
):
    user = await make_user(session_factory, "status@example.com", "INFLUENCER")

    async with session_factory() as db:
        db.add(ScrapeJob(
            user_id=user.id,
            platform=ScrapePlatform.INSTAGRAM,
            status=ScrapeStatus.ERROR,
            message="Could not fetch @ghost.",
        ))
        await db.commit()

    res = await client.get(
        f"/instagram/scrape-status/{user.id}", headers=auth_header(user)
    )

    assert res.status_code == 200
    assert res.json()["status"] == "error"
    assert "ghost" in res.json()["message"]


async def test_scrape_status_is_owner_scoped(client, session_factory):
    victim = await make_user(session_factory, "v@example.com", "INFLUENCER")
    attacker = await make_user(session_factory, "a@example.com", "INFLUENCER")

    res = await client.get(
        f"/instagram/scrape-status/{victim.id}", headers=auth_header(attacker)
    )

    assert res.status_code == 403


async def test_scrape_status_with_no_history(client, session_factory):
    user = await make_user(session_factory, "new@example.com", "INFLUENCER")

    res = await client.get(
        f"/instagram/scrape-status/{user.id}", headers=auth_header(user)
    )

    assert res.status_code == 200
    assert res.json()["status"] == "none"


# ---------------------------------------------------------------------------
# Cross-account channel claim
# ---------------------------------------------------------------------------

async def test_youtube_channel_cannot_be_stolen_by_a_second_account(
    session_factory, monkeypatch
):
    """
    The upsert used to match on channel_id alone, so a second user claiming the
    same channel overwrote the first user's row.
    """
    owner = await make_user(session_factory, "owner@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, owner.id, youtube_username="chan")
    thief = await make_user(session_factory, "thief@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, thief.id, youtube_username="chan")

    monkeypatch.setattr(
        "app.modules.youtube.service.AsyncSessionLocal", session_factory
    )

    async def fake_channel(username):
        return {
            "channel": {
                "channel_id": "UC_shared_channel", "username": username, "title": "T",
                "description": "", "profile_picture": "", "subscribers": 1,
                "total_views": 1, "total_videos": 1, "is_verified": False,
            },
            "videos": [],
        }

    monkeypatch.setattr(
        "app.modules.youtube.service.scrape_youtube_channel", fake_channel
    )

    from app.modules.youtube.service import scrape_and_store_youtube

    first = await scrape_and_store_youtube(owner.id)
    assert first["status"] == "success"

    second = await scrape_and_store_youtube(thief.id)
    assert second["status"] == "error"
    assert "already linked" in second["message"]

    # The channel still belongs to the original owner.
    from app.modules.youtube.models import YouTubeChannel

    async with session_factory() as db:
        channel = (await db.execute(
            select(YouTubeChannel).where(YouTubeChannel.channel_id == "UC_shared_channel")
        )).scalar()

    assert channel.user_id == owner.id


# ---------------------------------------------------------------------------
# Snapshot retention
# ---------------------------------------------------------------------------

async def test_old_snapshots_are_pruned_but_the_newest_is_kept(
    session_factory, monkeypatch
):
    """
    Instagram snapshots previously accumulated forever. Pruning must bound that
    growth without ever leaving a creator with no analytics.
    """
    from datetime import datetime, timedelta

    from app.core.config import settings
    from app.modules.instagram.models.instagram import InstagramPost, InstagramProfile

    user = await make_user(session_factory, "retain@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, user.id, instagram_username="retain")

    old = datetime.utcnow() - timedelta(days=settings.scrape_ttl_days + 30)
    async with session_factory() as db:
        db.add(InstagramProfile(user_id=user.id, username="retain", followers=10, scraped_at=old))
        db.add(InstagramPost(user_id=user.id, shortcode="old", likes=1, scraped_at=old))
        await db.commit()

    monkeypatch.setattr(
        "app.modules.instagram.services.instagram_scrapper.AsyncSessionLocal",
        session_factory,
    )

    async def fake_scrape(username):
        return {
            "profile": {
                "username": username, "full_name": "N", "bio": "", "profile_picture": "",
                "followers": 20, "following": 5, "posts_count": 1, "is_verified": False,
            },
            "posts": [],
        }

    monkeypatch.setattr(
        "app.modules.instagram.services.instagram_scrapper.scrape_instagram", fake_scrape
    )

    from app.modules.instagram.services.instagram_scrapper import scrape_and_store

    assert (await scrape_and_store(user.id))["status"] == "success"

    async with session_factory() as db:
        profiles = (await db.execute(
            select(InstagramProfile).where(InstagramProfile.user_id == user.id)
        )).scalars().all()
        posts = (await db.execute(
            select(InstagramPost).where(InstagramPost.user_id == user.id)
        )).scalars().all()

    # The stale snapshot is gone; the fresh one survives.
    assert len(profiles) == 1
    assert profiles[0].followers == 20
    assert not any(p.shortcode == "old" for p in posts)


async def test_pruning_never_removes_the_only_snapshot(session_factory, monkeypatch):
    """A creator who has not scraped in months must keep their last snapshot."""
    from datetime import datetime, timedelta

    from app.core.config import settings
    from app.modules.instagram.models.instagram import InstagramProfile
    from app.modules.instagram.services.instagram_scrapper import _prune_old_snapshots

    user = await make_user(session_factory, "lonely@example.com", "INFLUENCER")
    ancient = datetime.utcnow() - timedelta(days=settings.scrape_ttl_days + 365)

    async with session_factory() as db:
        db.add(InstagramProfile(user_id=user.id, username="lonely", followers=5, scraped_at=ancient))
        await db.commit()

    async with session_factory() as db:
        await _prune_old_snapshots(db, user.id)

    async with session_factory() as db:
        remaining = (await db.execute(
            select(InstagramProfile).where(InstagramProfile.user_id == user.id)
        )).scalars().all()

    assert len(remaining) == 1, "pruning must never leave a creator with no analytics"
