"""
Helpers for recording scrape attempts.

Kept deliberately small and failure-tolerant: bookkeeping must never be the
reason a scrape fails, so every function here swallows its own errors after
logging them.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.config import settings
from app.core.logging import logger
from app.modules.scraping.models import ScrapeJob, ScrapeStatus


async def start_job(db: AsyncSession, user_id: int, platform: str) -> ScrapeJob | None:
    """Record that a scrape has begun. Returns None if bookkeeping failed."""
    try:
        job = ScrapeJob(
            user_id=user_id,
            platform=platform,
            status=ScrapeStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job
    except Exception as e:
        logger.warning("Could not record scrape job start for user {}: {}", user_id, e)
        await db.rollback()
        return None


async def finish_job(
    db: AsyncSession,
    job: ScrapeJob | None,
    status: str,
    message: str | None = None,
) -> None:
    """Mark a scrape finished. No-op if the job row was never created."""
    if job is None:
        return
    try:
        job.status = status
        job.message = message
        job.finished_at = datetime.utcnow()
        await db.commit()
    except Exception as e:
        logger.warning("Could not record scrape job completion: {}", e)
        await db.rollback()


#: What the creator is told when their scrape was killed mid-flight.
STALLED_MESSAGE = (
    "This import was interrupted before it finished. Please start it again."
)


async def reap_stalled_jobs(db: AsyncSession, user_id: int | None = None) -> int:
    """
    Fail any scrape that has been "running" for longer than is plausible.

    Scrapes are in-process `BackgroundTasks`. A deploy, a crash, or Render
    spinning the service down kills them with no chance to record anything, so
    the row stays `running` forever and the creator watches a spinner that will
    never resolve — the exact invisible-failure this table was added to prevent,
    reappearing one level up.

    Reaping by **age** rather than by "everything running at startup" matters:
    the latter is correct only while exactly one instance exists, and would
    start failing live scrapes belonging to other workers the moment the service
    is scaled up.

    Pass `user_id` to limit the sweep to one creator (used on the read path);
    omit it for the boot-time sweep. Returns how many rows were failed.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=settings.scrape_stuck_after_minutes)

    try:
        query = select(ScrapeJob).where(
            ScrapeJob.status == ScrapeStatus.RUNNING,
            ScrapeJob.started_at < cutoff,
        )
        if user_id is not None:
            query = query.where(ScrapeJob.user_id == user_id)

        stalled = list((await db.execute(query)).scalars().all())
        for job in stalled:
            job.status = ScrapeStatus.ERROR
            job.message = STALLED_MESSAGE
            job.finished_at = datetime.utcnow()

        if stalled:
            await db.commit()
            logger.warning(
                "Failed {} scrape job(s) left running by a restart or crash",
                len(stalled),
            )
        return len(stalled)
    except Exception as e:
        # Bookkeeping must never be the reason a request fails.
        logger.warning("Could not reap stalled scrape jobs: {}", e)
        await db.rollback()
        return 0


async def latest_job(db: AsyncSession, user_id: int, platform: str) -> ScrapeJob | None:
    """
    Most recent scrape attempt for a user on one platform.

    Takes the caller's session rather than opening its own: request handlers
    should always use the request-scoped session, and a function that quietly
    creates its own is invisible to dependency overrides.

    Reaps this user's stalled jobs first, so the status endpoint self-heals on
    the next poll instead of waiting for a restart. Scoped to one user to keep
    the write bounded on what is otherwise a read path.
    """
    await reap_stalled_jobs(db, user_id=user_id)

    result = await db.execute(
        select(ScrapeJob)
        .where(ScrapeJob.user_id == user_id, ScrapeJob.platform == platform)
        .order_by(ScrapeJob.started_at.desc(), ScrapeJob.id.desc())
        .limit(1)
    )
    return result.scalar()


@asynccontextmanager
async def track_scrape(db: AsyncSession, user_id: int, platform: str):
    """
    Context manager that records a scrape attempt end to end.

        async with track_scrape(db, user_id, "instagram") as job:
            ...
            await job.succeed("Imported 15 posts")

    An uncaught exception inside the block is recorded as a failure and
    re-raised, so a crash can never leave a job stuck in "running".
    """
    job = await start_job(db, user_id, platform)

    class Handle:
        async def succeed(self, message: str | None = None) -> None:
            await finish_job(db, job, ScrapeStatus.SUCCESS, message)

        async def fail(self, message: str) -> None:
            await finish_job(db, job, ScrapeStatus.ERROR, message)

    handle = Handle()
    try:
        yield handle
    except Exception as e:
        await handle.fail(f"Scrape failed unexpectedly: {e}")
        raise
