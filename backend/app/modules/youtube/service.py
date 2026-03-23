from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from dateutil import parser as date_parser

from app.modules.users.models import User, CreatorProfile
from app.modules.youtube.models import YouTubeChannel, YouTubeVideo
from app.modules.youtube.scrapper import scrape_youtube_channel


async def scrape_and_store_youtube(user_id: int, db: AsyncSession):
    """
    Scrape YouTube channel data using username from CreatorProfile table
    and store results in YouTubeChannel and YouTubeVideo tables
    """
    print("🟡 Starting YouTube scrape for user:", user_id)

    # Get the user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()

    if not user:
        print("❌ User not found")
        return {"status": "error", "message": "User not found"}

    # Get the creator profile
    creator_result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == user_id)
    )
    creator_profile = creator_result.scalar()

    if not creator_profile:
        print("❌ Creator profile not found")
        return {"status": "error", "message": "Creator profile not found"}

    # Use youtube_username field from CreatorProfile
    youtube_username = creator_profile.youtube_username

    if not youtube_username:
        print("❌ No YouTube username in creator profile")
        return {"status": "error", "message": "No YouTube username"}

    print("🔥 Scraping YouTube:", youtube_username)

    try:
        # Call YouTube scraper
        data = await scrape_youtube_channel(youtube_username)
    except Exception as e:
        print("❌ YouTube scraper failed:", str(e))
        return {"status": "error", "message": str(e)}

    print("📦 Scraped channel data:", data["channel"])
    print("📦 Videos scraped:", len(data["videos"]))

    # Use naive UTC datetime for database (TIMESTAMP WITHOUT TIME ZONE)
    now_utc = datetime.utcnow()

    # Check if channel already exists
    existing_channel = await db.execute(
        select(YouTubeChannel).where(YouTubeChannel.channel_id == data["channel"]["channel_id"])
    )
    channel = existing_channel.scalar()

    if channel:
        # Update existing channel
        for key, value in data["channel"].items():
            if key != "channel_id":
                setattr(channel, key, value)
        channel.scraped_at = now_utc
        
        # Delete old videos
        old_videos = (await db.execute(
            select(YouTubeVideo).where(YouTubeVideo.channel_id == channel.channel_id)
        )).scalars().all()
        
        for video in old_videos:
            await db.delete(video)
    else:
        # Create new channel
        channel = YouTubeChannel(
            user_id=user.id,
            scraped_at=now_utc,
            **data["channel"]
        )
        db.add(channel)

    # Save videos data - parse datetime strings and convert to naive UTC
    for video in data["videos"]:
        try:
            # Parse published_at from ISO 8601 string if it's a string
            if isinstance(video.get("published_at"), str):
                parsed_dt = date_parser.isoparse(video["published_at"])
                # Convert to naive UTC if timezone-aware
                if parsed_dt.tzinfo is not None:
                    # Convert to UTC and remove timezone info
                    parsed_dt = parsed_dt.astimezone(timezone.utc).replace(tzinfo=None)
                video["published_at"] = parsed_dt
        except (ValueError, TypeError) as e:
            print(f"⚠️ Error parsing published_at date: {e}")
            video["published_at"] = now_utc

        db.add(
            YouTubeVideo(
                user_id=user.id,
                channel_id=data["channel"]["channel_id"],
                scraped_at=now_utc,
                **video
            )
        )

    await db.commit()

    print("✅ YouTube data committed to DB")
    return {"status": "success", "message": "YouTube channel scraped and stored"}
