import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.modules.users.models import User, CreatorProfile
from app.modules.instagram.workers.instagram_worker import run_scrape


async def run_scraper_jobs():
    """Run scraper jobs for all users with Instagram usernames"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CreatorProfile).where(CreatorProfile.username.isnot(None))
        )
        users = result.scalars().all()

        for user in users:
            run_scrape.delay(user.id)


if __name__ == "__main__":
    asyncio.run(run_scraper_jobs())
