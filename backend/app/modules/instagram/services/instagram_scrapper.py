from sqlalchemy import select
from datetime import datetime, timezone
from dateutil import parser as date_parser

from app.core.database import AsyncSessionLocal
from app.modules.users.models import User, CreatorProfile
from app.modules.instagram.models.instagram import InstagramProfile, InstagramPost
from app.modules.instagram.scrapper.scrapper import scrape_instagram


async def scrape_and_store(user_id: int):
    """
    Scrape Instagram profile data using username from CreatorProfile table
    and store results in InstagramProfile and InstagramPost tables.
    Creates its own DB session since this runs as a background task.
    """
    print("🟡 Starting scrape for user:", user_id)

    async with AsyncSessionLocal() as db:
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

        # Use instagram_username field instead of username
        instagram_username = creator_profile.instagram_username

        if not instagram_username:
            print("❌ No Instagram username in creator profile")
            return {"status": "error", "message": "No Instagram username"}

        print("🔥 Scraping Instagram:", instagram_username)

        try:
            # Call Apify service via scraper
            data = await scrape_instagram(instagram_username)
        except Exception as e:
            print("❌ Scraper failed:", str(e))
            return {"status": "error", "message": str(e)}

        print("📦 Scraped profile data:", data["profile"])
        print("📦 Posts scraped:", len(data["posts"]))

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
                print(f"⚠️ Error parsing posted_at date: {e}")
                post["posted_at"] = now_utc

            db.add(
                InstagramPost(
                    user_id=user.id,
                    scraped_at=now_utc,
                    **post
                )
            )

        await db.commit()

        print("✅ Data committed to DB")
        return {"status": "success", "message": "Profile scraped and stored"}

