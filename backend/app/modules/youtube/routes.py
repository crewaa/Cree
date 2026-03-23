from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.common.dependencies import get_db
from app.modules.youtube.service import scrape_and_store_youtube
from app.modules.youtube.models import YouTubeChannel, YouTubeVideo

router = APIRouter(prefix="/youtube", tags=["YouTube"])


@router.post("/scrape/{user_id}")
async def scrape_youtube_now(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Trigger YouTube scraping for a user (via their CreatorProfile)"""
    background_tasks.add_task(scrape_and_store_youtube, user_id, db)
    return {"status": "scraping", "message": "YouTube channel scraping started"}


@router.get("/analytics/{user_id}")
async def youtube_analytics(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get latest YouTube channel and videos analytics for a user"""
    
    channel_result = await db.execute(
        select(YouTubeChannel)
        .where(YouTubeChannel.user_id == user_id)
        .order_by(YouTubeChannel.scraped_at.desc())
    )
    channel = channel_result.scalars().first()

    if not channel:
        return {
            "status": "no_data",
            "message": "No YouTube channel data found. Please scrape first.",
            "channel": None,
            "videos": []
        }

    videos_result = await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.user_id == user_id)
        .order_by(YouTubeVideo.published_at.desc())
        .limit(15)
    )
    videos = videos_result.scalars().all()

    return {
        "status": "success",
        "channel": {
            "id": channel.id,
            "channel_id": channel.channel_id,
            "username": channel.username,
            "title": channel.title,
            "description": channel.description,
            "profile_picture": channel.profile_picture,
            "subscribers": channel.subscribers,
            "total_views": channel.total_views,
            "total_videos": channel.total_videos,
            "is_verified": channel.is_verified,
            "scraped_at": channel.scraped_at
        },
        "videos": [
            {
                "id": video.id,
                "video_id": video.video_id,
                "title": video.title,
                "description": video.description,
                "thumbnail": video.thumbnail,
                "views": video.views,
                "likes": video.likes,
                "comments": video.comments,
                "duration": video.duration,
                "published_at": video.published_at,
                "scraped_at": video.scraped_at
            }
            for video in videos
        ]
    }
