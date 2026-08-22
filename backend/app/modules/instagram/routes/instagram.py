from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.common.dependencies import get_db, require_self_or_admin
from app.common.rate_limit import rate_limit_user
from app.modules.scraping.models import ScrapePlatform
from app.modules.scraping.service import latest_job
from app.modules.users.models import User
from app.modules.instagram.services.instagram_scrapper import scrape_and_store
from app.modules.instagram.models.instagram import InstagramProfile, InstagramPost

router = APIRouter(prefix="/instagram", tags=["Instagram"])


# Each run costs real money/quota, so it is throttled per user account.
@router.post(
    "/scrape/{user_id}",
    dependencies=[rate_limit_user(6, 3600, "ig_scrape")],
)
async def scrape_now(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_self_or_admin),
):
    """
    Trigger Instagram scraping for a user (via their CreatorProfile).

    Requires authentication: a user may only scrape their own profile.
    Each run costs an Apify actor call, so this must never be open.
    """
    background_tasks.add_task(scrape_and_store, user_id)
    return {"status": "scraping", "message": "Instagram profile scraping started"}


@router.get("/analytics/{user_id}")
async def analytics(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_self_or_admin),
):
    """Get latest Instagram profile and posts analytics for a user"""

    profile_result = await db.execute(
        select(InstagramProfile)
        .where(InstagramProfile.user_id == user_id)
        .order_by(InstagramProfile.scraped_at.desc())
    )
    profile = profile_result.scalars().first()

    if not profile:
        return {
            "status": "no_data",
            "message": "No Instagram profile data found. Please scrape first.",
            "profile": None,
            "posts": []
        }

    posts_result = await db.execute(
        select(InstagramPost)
        .where(
            InstagramPost.user_id == user_id,
            InstagramPost.scraped_at == profile.scraped_at,
        )
        .order_by(InstagramPost.posted_at.desc())
        .limit(15)
    )
    posts = posts_result.scalars().all()

    return {
        "status": "success",
        "profile": {
            "id": profile.id,
            "username": profile.username,
            "full_name": profile.full_name,
            "bio": profile.bio,
            "profile_picture": profile.profile_picture,
            "followers": profile.followers,
            "following": profile.following,
            "posts_count": profile.posts_count,
            "is_verified": profile.is_verified,
            "scraped_at": profile.scraped_at
        },
        "posts": [
            {
                "id": post.id,
                "shortcode": post.shortcode,
                "likes": post.likes,
                "comments": post.comments,
                "is_video": post.is_video,
                "views": post.views,
                "caption": post.caption,
                "posted_at": post.posted_at,
                "scraped_at": post.scraped_at
            }
            for post in posts
        ]
    }


@router.get("/scrape-status/{user_id}")
async def instagram_scrape_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_self_or_admin),
):
    """
    Outcome of the most recent Instagram scrape for this user.

    Scrapes run in the background, so without this the client has no way to
    distinguish "still running" from "failed" — it could only poll the
    analytics endpoint and eventually give up, showing an empty dashboard with
    no explanation.
    """
    job = await latest_job(db, user_id, ScrapePlatform.INSTAGRAM)

    if job is None:
        return {"status": "none", "message": None, "finished_at": None}

    return {
        "status": job.status,
        "message": job.message,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
