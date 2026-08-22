"""
Tests for recovering scrapes that a restart killed.

Scrapes run as in-process `BackgroundTasks`. A deploy, a crash, or Render
spinning a free service down takes them with it, and the `scrape_jobs` row stays
`running` forever. The creator then watches a spinner that will never resolve —
which is the same invisible failure `scrape_jobs` was introduced to eliminate,
just moved up a level.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.modules.scraping.models import ScrapeJob, ScrapePlatform, ScrapeStatus
from app.modules.scraping.service import STALLED_MESSAGE, latest_job, reap_stalled_jobs
from tests.conftest import auth_header, make_user


async def _job(session_factory, user_id, *, minutes_ago, status=ScrapeStatus.RUNNING,
               platform=ScrapePlatform.INSTAGRAM):
    async with session_factory() as db:
        job = ScrapeJob(
            user_id=user_id,
            platform=platform,
            status=status,
            started_at=datetime.utcnow() - timedelta(minutes=minutes_ago),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
    return job


async def test_a_scrape_stuck_running_is_failed(session_factory):
    user = await make_user(session_factory, "stuck@example.com", "INFLUENCER")
    await _job(session_factory, user.id, minutes_ago=settings.scrape_stuck_after_minutes + 5)

    async with session_factory() as db:
        assert await reap_stalled_jobs(db) == 1

    async with session_factory() as db:
        job = (await db.execute(select(ScrapeJob))).scalar()

    assert job.status == ScrapeStatus.ERROR
    assert job.message == STALLED_MESSAGE
    assert job.finished_at is not None


async def test_a_scrape_still_within_its_window_is_left_alone(session_factory):
    """
    The whole point of reaping by age. Killing a genuinely-running scrape would
    tell the creator it failed while it was busy succeeding.
    """
    user = await make_user(session_factory, "busy@example.com", "INFLUENCER")
    await _job(session_factory, user.id, minutes_ago=1)

    async with session_factory() as db:
        assert await reap_stalled_jobs(db) == 0

    async with session_factory() as db:
        job = (await db.execute(select(ScrapeJob))).scalar()

    assert job.status == ScrapeStatus.RUNNING


async def test_finished_jobs_are_never_touched(session_factory):
    user = await make_user(session_factory, "done@example.com", "INFLUENCER")
    await _job(session_factory, user.id, minutes_ago=600, status=ScrapeStatus.SUCCESS)

    async with session_factory() as db:
        assert await reap_stalled_jobs(db) == 0

    async with session_factory() as db:
        job = (await db.execute(select(ScrapeJob))).scalar()

    assert job.status == ScrapeStatus.SUCCESS
    assert job.message is None


async def test_a_user_scoped_sweep_leaves_other_users_alone(session_factory):
    """
    The read path reaps only the caller's jobs. Sweeping everyone on every poll
    would turn a status check into a table-wide write.
    """
    mine = await make_user(session_factory, "mine@example.com", "INFLUENCER")
    theirs = await make_user(session_factory, "theirs@example.com", "INFLUENCER")
    stale = settings.scrape_stuck_after_minutes + 5
    await _job(session_factory, mine.id, minutes_ago=stale)
    await _job(session_factory, theirs.id, minutes_ago=stale)

    async with session_factory() as db:
        assert await reap_stalled_jobs(db, user_id=mine.id) == 1

    async with session_factory() as db:
        others = (await db.execute(
            select(ScrapeJob).where(ScrapeJob.user_id == theirs.id)
        )).scalar()

    assert others.status == ScrapeStatus.RUNNING


async def test_the_status_endpoint_self_heals(client, session_factory):
    """
    A creator should not have to wait for the next deploy to be told the truth.
    Polling the status endpoint is what they are already doing, so that is where
    the recovery has to land.
    """
    user = await make_user(session_factory, "poll@example.com", "INFLUENCER")
    await _job(session_factory, user.id,
               minutes_ago=settings.scrape_stuck_after_minutes + 5)

    res = await client.get(
        f"/instagram/scrape-status/{user.id}", headers=auth_header(user)
    )

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == ScrapeStatus.ERROR
    assert "interrupted" in body["message"].lower()


async def test_latest_job_reaps_before_reading(session_factory):
    user = await make_user(session_factory, "latest@example.com", "INFLUENCER")
    await _job(session_factory, user.id,
               minutes_ago=settings.scrape_stuck_after_minutes + 5)

    async with session_factory() as db:
        job = await latest_job(db, user.id, ScrapePlatform.INSTAGRAM)

    assert job.status == ScrapeStatus.ERROR


async def test_the_threshold_is_configurable(session_factory, monkeypatch):
    """A slower scraping backend should be a config change, not a code change."""
    user = await make_user(session_factory, "cfg@example.com", "INFLUENCER")
    await _job(session_factory, user.id, minutes_ago=20)

    monkeypatch.setattr(settings, "scrape_stuck_after_minutes", 60)
    async with session_factory() as db:
        assert await reap_stalled_jobs(db) == 0

    monkeypatch.setattr(settings, "scrape_stuck_after_minutes", 10)
    async with session_factory() as db:
        assert await reap_stalled_jobs(db) == 1
