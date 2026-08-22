from sqlalchemy import select
from datetime import datetime, timezone
from dateutil import parser as date_parser

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.modules.users.models import User, CreatorProfile
from app.modules.youtube.models import YouTubeChannel, YouTubeVideo
from app.modules.youtube.scrapper import scrape_youtube_channel
from app.modules.scraping.models import ScrapePlatform
from app.modules.scraping.service import track_scrape


async def scrape_and_store_youtube(user_id: int):
    """
    Scrape YouTube channel data using the username on the user's CreatorProfile
    and store the result in youtube_channels / youtube_videos.

    Opens its own database session because this runs as a FastAPI BackgroundTask,
    after the request-scoped session has already been closed.
    """
    logger.info("Starting YouTube scrape for user {}", user_id)

    async with AsyncSessionLocal() as db:
      async with track_scrape(db, user_id, ScrapePlatform.YOUTUBE) as job:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar()

        if not user:
            logger.warning("YouTube scrape aborted: user {} not found", user_id)
            await job.fail("User not found")
            return {"status": "error", "message": "User not found"}

        creator_result = await db.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == user_id)
        )
        creator_profile = creator_result.scalar()

        if not creator_profile:
            logger.warning("YouTube scrape aborted: no creator profile for user {}", user_id)
            await job.fail("Complete your creator profile before importing analytics.")
            return {"status": "error", "message": "Creator profile not found"}

        youtube_username = creator_profile.youtube_username

        if not youtube_username:
            logger.warning("YouTube scrape aborted: no YouTube username for user {}", user_id)
            await job.fail("No YouTube username set on your profile.")
            return {"status": "error", "message": "No YouTube username"}

        logger.info("Scraping YouTube channel '{}' for user {}", youtube_username, user_id)

        try:
            data = await scrape_youtube_channel(youtube_username)
        except Exception as e:
            logger.error("YouTube scraper failed for user {}: {}", user_id, e)
            await job.fail(
                f"Could not fetch the channel '{youtube_username}'. Check the handle "
                "is correct, or try again later."
            )
            return {"status": "error", "message": str(e)}

        scraped_channel_id = data["channel"]["channel_id"]
        logger.info(
            "Scraped YouTube channel {} with {} videos for user {}",
            scraped_channel_id, len(data["videos"]), user_id,
        )

        # Naive UTC to match the TIMESTAMP WITHOUT TIME ZONE columns.
        now_utc = datetime.utcnow()

        # Look up the channel scoped to THIS user. Matching on channel_id alone
        # would let one user's scrape overwrite another user's channel row when
        # two accounts claim the same channel.
        existing_channel = await db.execute(
            select(YouTubeChannel).where(
                YouTubeChannel.user_id == user_id,
                YouTubeChannel.channel_id == scraped_channel_id,
            )
        )
        channel = existing_channel.scalar()

        if channel is None:
            # channel_id is globally unique, so check whether another account
            # has already claimed it before attempting an insert that would
            # violate the constraint.
            claimed = await db.execute(
                select(YouTubeChannel).where(
                    YouTubeChannel.channel_id == scraped_channel_id
                )
            )
            other = claimed.scalar()
            if other is not None:
                logger.warning(
                    "YouTube channel {} is already linked to user {}; refusing to "
                    "reassign it to user {}",
                    scraped_channel_id, other.user_id, user_id,
                )
                await job.fail(
                    "This YouTube channel is already linked to another Crewaa account."
                )
                return {
                    "status": "error",
                    "message": "This YouTube channel is already linked to another account",
                }

        if channel:
            for key, value in data["channel"].items():
                if key != "channel_id":
                    setattr(channel, key, value)
            channel.scraped_at = now_utc

            # Videos are replaced wholesale on each scrape.
            old_videos = (await db.execute(
                select(YouTubeVideo).where(
                    YouTubeVideo.channel_id == channel.channel_id,
                    YouTubeVideo.user_id == user_id,
                )
            )).scalars().all()

            for video in old_videos:
                await db.delete(video)
        else:
            channel = YouTubeChannel(
                user_id=user.id,
                scraped_at=now_utc,
                **data["channel"]
            )
            db.add(channel)
            # Flush so the FK target exists before videos reference it.
            await db.flush()

        for video in data["videos"]:
            try:
                if isinstance(video.get("published_at"), str):
                    parsed_dt = date_parser.isoparse(video["published_at"])
                    if parsed_dt.tzinfo is not None:
                        parsed_dt = parsed_dt.astimezone(timezone.utc).replace(tzinfo=None)
                    video["published_at"] = parsed_dt
            except (ValueError, TypeError) as e:
                logger.warning("Could not parse published_at ({}), defaulting to now", e)
                video["published_at"] = now_utc

            db.add(
                YouTubeVideo(
                    user_id=user.id,
                    channel_id=scraped_channel_id,
                    scraped_at=now_utc,
                    **video
                )
            )

        await db.commit()

        logger.info("YouTube data stored for user {}", user_id)
        await job.succeed(
            f"Imported {len(data['videos'])} videos from '{youtube_username}'."
        )
        return {"status": "success", "message": "YouTube channel scraped and stored"}
