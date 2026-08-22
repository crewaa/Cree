from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.modules.users.models import User, CreatorProfile
from app.modules.instagram.models.instagram import InstagramProfile, InstagramPost
from app.modules.instagram.scrapper.scrapper import scrape_instagram
from app.modules.scraping.models import ScrapePlatform
from app.modules.scraping.service import track_scrape


async def _prune_old_snapshots(db, user_id: int) -> None:
    """
    Drop Instagram snapshots older than the retention window.

    Every scrape appends a profile row plus up to 15 posts and nothing ever
    removed them, so storage grew without bound for the lifetime of an account.
    The newest snapshot is always kept, even if it is older than the window, so
    a creator who has not scraped in a while does not lose their analytics.
    """
    if settings.scrape_ttl_days <= 0:
        return

    cutoff = datetime.utcnow() - timedelta(days=settings.scrape_ttl_days)

    try:
        newest = (await db.execute(
            select(InstagramProfile.scraped_at)
            .where(InstagramProfile.user_id == user_id)
            .order_by(InstagramProfile.scraped_at.desc())
            .limit(1)
        )).scalar()

        if newest is None:
            return

        await db.execute(
            delete(InstagramPost).where(
                InstagramPost.user_id == user_id,
                InstagramPost.scraped_at < cutoff,
                InstagramPost.scraped_at != newest,
            )
        )
        await db.execute(
            delete(InstagramProfile).where(
                InstagramProfile.user_id == user_id,
                InstagramProfile.scraped_at < cutoff,
                InstagramProfile.scraped_at != newest,
            )
        )
        await db.commit()
    except Exception as e:
        # Housekeeping must never fail a scrape that otherwise succeeded.
        logger.warning("Snapshot pruning failed for user {}: {}", user_id, e)
        await db.rollback()


async def scrape_and_store(user_id: int):
    """
    Scrape Instagram profile data using username from CreatorProfile table
    and store results in InstagramProfile and InstagramPost tables.
    Creates its own DB session since this runs as a background task.
    """
    logger.info("Starting Instagram scrape for user {}", user_id)

    async with AsyncSessionLocal() as db:
      async with track_scrape(db, user_id, ScrapePlatform.INSTAGRAM) as job:
        # Get the user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar()

        if not user:
            logger.warning("Instagram scrape aborted: user {} not found", user_id)
            await job.fail("User not found")
            return {"status": "error", "message": "User not found"}

        # Get the creator profile
        creator_result = await db.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == user_id)
        )
        creator_profile = creator_result.scalar()

        if not creator_profile:
            logger.warning("Instagram scrape aborted: no creator profile for user {}", user_id)
            await job.fail("Complete your creator profile before importing analytics.")
            return {"status": "error", "message": "Creator profile not found"}

        # Use instagram_username field instead of username
        instagram_username = creator_profile.instagram_username

        if not instagram_username:
            logger.warning("Instagram scrape aborted: no username for user {}", user_id)
            await job.fail("No Instagram username set on your profile.")
            return {"status": "error", "message": "No Instagram username"}

        logger.info("Scraping Instagram '{}' for user {}", instagram_username, user_id)

        try:
            # Call Apify service via scraper
            data = await scrape_instagram(instagram_username)
        except Exception as e:
            logger.error("Instagram scraper failed for user {}: {}", user_id, e)
            await job.fail(
                f"Could not fetch @{instagram_username}. The account may be private, "
                "renamed, or Instagram may be rate-limiting us. Please try again later."
            )
            return {"status": "error", "message": str(e)}

        logger.info(
            "Scraped Instagram profile for user {} with {} posts",
            user_id, len(data["posts"]),
        )

        # Use naive UTC datetime for database (TIMESTAMP WITHOUT TIME ZONE)
        now_utc = datetime.utcnow()

        # Save profile data
        profile = InstagramProfile(
            user_id=user.id,
            scraped_at=now_utc,
            **data["profile"]
        )

        db.add(profile)

        # Save posts data - parse datetime strings and convert to naive UTC
        for post in data["posts"]:
            try:
                # Parse posted_at from ISO 8601 string if it's a string
                if isinstance(post.get("posted_at"), str):
                    parsed_dt = date_parser.isoparse(post["posted_at"])
                    # Convert to naive UTC if timezone-aware
                    if parsed_dt.tzinfo is not None:
                        # Convert to UTC and remove timezone info
                        parsed_dt = parsed_dt.astimezone(timezone.utc).replace(tzinfo=None)
                    post["posted_at"] = parsed_dt
            except (ValueError, TypeError) as e:
                logger.warning("Could not parse posted_at ({}), defaulting to now", e)
                post["posted_at"] = now_utc

            db.add(
                InstagramPost(
                    user_id=user.id,
                    scraped_at=now_utc,
                    **post
                )
            )

        await db.commit()

        await _prune_old_snapshots(db, user_id)

        logger.info("Instagram data stored for user {}", user_id)
        await job.succeed(f"Imported {len(data['posts'])} posts from @{instagram_username}.")
        return {"status": "success", "message": "Profile scraped and stored"}

