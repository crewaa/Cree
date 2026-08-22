from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.common.dependencies import get_db, require_self_or_admin
from app.common.rate_limit import rate_limit_user
from app.modules.scraping.models import ScrapePlatform
from app.modules.scraping.service import latest_job
from app.modules.users.models import User
from app.modules.youtube.service import scrape_and_store_youtube
from app.modules.youtube.models import YouTubeChannel, YouTubeVideo

router = APIRouter(prefix="/youtube", tags=["YouTube"])


# Each run costs real money/quota, so it is throttled per user account.
@router.post(
    "/scrape/{user_id}",
    dependencies=[rate_limit_user(6, 3600, "yt_scrape")],
)
async def scrape_youtube_now(
    user_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_self_or_admin),
):
    """
    Trigger YouTube scraping for a user (via their CreatorProfile).

    Requires authentication: a user may only scrape their own channel.
    Each run costs ~100 YouTube Data API quota units, so this must never be open.

    Note: the request-scoped session is deliberately NOT passed to the
    background task — it is closed as soon as this response is returned.
    scrape_and_store_youtube opens its own session.
    """
    background_tasks.add_task(scrape_and_store_youtube, user_id)
    return {"status": "scraping", "message": "YouTube channel scraping started"}


@router.get("/analytics/{user_id}")
async def youtube_analytics(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_self_or_admin),
):
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


@router.get("/scrape-status/{user_id}")
async def youtube_scrape_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_self_or_admin),
):
    """
    Outcome of the most recent YouTube scrape for this user.

    Scrapes run in the background, so without this the client has no way to
    distinguish "still running" from "failed" — it could only poll the
    analytics endpoint and eventually give up, showing an empty dashboard with
    no explanation.
    """
    job = await latest_job(db, user_id, ScrapePlatform.YOUTUBE)

    if job is None:
        return {"status": "none", "message": None, "finished_at": None}

    return {
        "status": job.status,
        "message": job.message,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }
