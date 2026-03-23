from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.common.dependencies import get_db
from app.modules.instagram.services.instagram_scrapper import scrape_and_store
from app.modules.instagram.models.instagram import InstagramProfile, InstagramPost

router = APIRouter(prefix="/instagram", tags=["Instagram"])


@router.post("/scrape/{user_id}")
async def scrape_now(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger Instagram scraping for a user (via their CreatorProfile)"""
    background_tasks.add_task(scrape_and_store, user_id)
    return {"status": "scraping", "message": "Instagram profile scraping started"}


@router.get("/analytics/{user_id}")
async def analytics(user_id: int, db: AsyncSession = Depends(get_db)):
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
