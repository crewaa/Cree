"""
AI Routes - Discover Creators & Brand Deals
"""

import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.dependencies import get_db, get_current_user
from app.modules.users.models import User, CreatorProfile, BrandProfile
from app.modules.instagram.models.instagram import InstagramProfile, InstagramPost
from app.modules.youtube.models import YouTubeChannel, YouTubeVideo
from app.modules.ai.schemas import (
    DiscoverCreatorsRequest,
    DiscoverCreatorsResponse,
    RankedCreator,
    BrandDealsResponse,
    BrandDealOpportunity,
)
from app.modules.ai.ai_service import BrandCreatorRankingEngine, AnonymousOpportunityEngine

router = APIRouter(prefix="/ai", tags=["AI Engine"])


def _safe_json_parse(value: str | None) -> list:
    """Parse a JSON string list, return empty list if None or invalid."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


async def _build_creator_payload(user_id: int, creator: CreatorProfile, db: AsyncSession) -> dict:
    """Build the creator feature payload from DB data for AI engine consumption."""

    # Get Instagram data
    ig_result = await db.execute(
        select(InstagramProfile)
        .where(InstagramProfile.user_id == user_id)
        .order_by(InstagramProfile.scraped_at.desc())
    )
    ig_profile = ig_result.scalars().first()

    ig_posts_result = await db.execute(
        select(InstagramPost)
        .where(InstagramPost.user_id == user_id)
        .order_by(InstagramPost.posted_at.desc())
        .limit(10)
    )
    ig_posts = ig_posts_result.scalars().all()

    # Get YouTube data
    yt_result = await db.execute(
        select(YouTubeChannel)
        .where(YouTubeChannel.user_id == user_id)
        .order_by(YouTubeChannel.scraped_at.desc())
    )
    yt_channel = yt_result.scalars().first()

    yt_videos_result = await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.user_id == user_id)
        .order_by(YouTubeVideo.published_at.desc())
        .limit(10)
    )
    yt_videos = yt_videos_result.scalars().all()

    platforms = []

    if ig_profile:
        avg_likes = 0
        avg_comments = 0
        if ig_posts:
            avg_likes = sum(p.likes or 0 for p in ig_posts) // len(ig_posts)
            avg_comments = sum(p.comments or 0 for p in ig_posts) // len(ig_posts)

        engagement_rate = 0
        if ig_profile.followers and ig_profile.followers > 0:
            engagement_rate = round((avg_likes + avg_comments) / ig_profile.followers * 100, 2)

        platforms.append({
            "platform": "instagram",
            "username": ig_profile.username,
            "verified": ig_profile.is_verified,
            "bio": ig_profile.bio,
            "followers": ig_profile.followers,
            "following": ig_profile.following,
            "engagement": {
                "avg_likes": avg_likes,
                "avg_comments": avg_comments,
                "engagement_rate": engagement_rate,
            },
            "recent_posts": [
                {
                    "type": "reel" if p.is_video else "image",
                    "caption": (p.caption or "")[:200],
                    "likes": p.likes,
                    "comments": p.comments,
                }
                for p in ig_posts[:5]
            ],
        })

    if yt_channel:
        platforms.append({
            "platform": "youtube",
            "username": yt_channel.username,
            "title": yt_channel.title,
            "description": (yt_channel.description or "")[:200],
            "subscribers": yt_channel.subscribers,
            "total_views": yt_channel.total_views,
            "total_videos": yt_channel.total_videos,
            "recent_videos": [
                {
                    "title": v.title,
                    "views": v.views,
                    "likes": v.likes,
                    "comments": v.comments,
                }
                for v in yt_videos[:5]
            ],
        })

    return {
        "creator_identity": {
            "id": str(creator.user_id),
            "name": creator.full_name,
            "primary_niche": creator.category,
            "location": creator.location,
            "pricing": "Mid",  # default for now
        },
        "platforms": platforms,
    }


def _build_brand_payload(brand: BrandProfile) -> dict:
    """Build brand feature payload from DB data for AI engine consumption."""
    return {
        "brand_identity": {
            "brand_name": brand.brand_name,
            "industry": brand.industry,
            "campaign_goal": brand.campaign_goal,
            "budget_range": brand.budget_range,
            "target_location": brand.target_location or "India",
            "target_languages": _safe_json_parse(brand.target_languages) or ["English"],
        },
        "platform_preferences": _safe_json_parse(brand.platform_preferences) or ["instagram"],
    }


# =============================================================================
# Discover Creators - Brand finds matching influencers
# =============================================================================

@router.post("/discover-creators", response_model=DiscoverCreatorsResponse)
async def discover_creators(
    request: DiscoverCreatorsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Brand submits campaign requirements, AI ranks all creators from DB."""
    if current_user.role != "BRAND":
        raise HTTPException(403, "Only brands can discover creators")

    # Build brand data from request
    brand_data = {
        "brand_identity": {
            "brand_name": "Your Brand",  # anonymous for the prompt
            "industry": request.niche,
            "campaign_goal": request.campaign_goal,
            "budget_range": request.budget_range,
            "target_location": request.target_location or "India",
            "target_languages": request.target_languages or ["English"],
        },
        "platform_preferences": request.platform_preferences or ["instagram"],
    }

    # Also try to fetch brand profile to enrich data
    brand_profile_result = await db.execute(
        select(BrandProfile).where(BrandProfile.user_id == current_user.id)
    )
    brand_profile = brand_profile_result.scalar()

    if brand_profile:
        brand_data["brand_identity"]["brand_name"] = brand_profile.brand_name
        brand_data["brand_identity"]["industry"] = brand_profile.industry

    # Fetch all creator profiles
    creators_result = await db.execute(select(CreatorProfile))
    creators = creators_result.scalars().all()

    if not creators:
        return DiscoverCreatorsResponse(
            ranked_creators=[],
            final_recommendation="No creators found in the database. Please wait for creators to sign up."
        )

    # Build creator payloads
    creators_data = []
    for creator in creators:
        payload = await _build_creator_payload(creator.user_id, creator, db)
        creators_data.append(payload)

    # Run AI ranking
    try:
        engine = BrandCreatorRankingEngine()
        result = engine.rank_creators(brand_data, creators_data)
    except RuntimeError as e:
        # Rate limit / quota exceeded
        raise HTTPException(429, f"AI Engine rate-limited. Please wait a minute and try again.")
    except Exception as e:
        raise HTTPException(500, f"AI Engine error: {str(e)}")

    # Parse result
    ranked = []
    for c in result.get("ranked_creators", []):
        ranked.append(RankedCreator(
            creator_id=c.get("creator_id", "unknown"),
            creator_name=c.get("creator_name"),
            fit_level=c.get("fit_level", "Low"),
            score_reasoning=c.get("score_reasoning", []),
            risks=c.get("risks", []),
            recommended_campaign_type=c.get("recommended_campaign_type"),
        ))

    return DiscoverCreatorsResponse(
        ranked_creators=ranked,
        final_recommendation=result.get("final_recommendation"),
    )


# =============================================================================
# Brand Deals - Influencer sees anonymous brand opportunities
# =============================================================================

@router.post("/brand-deals", response_model=BrandDealsResponse)
async def get_brand_deals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Influencer requests available brand deals. AI generates anonymous opportunities."""
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only influencers can view brand deals")

    # Get influencer's creator profile
    creator_result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    creator = creator_result.scalar()

    if not creator:
        raise HTTPException(404, "Please complete your creator profile first")

    # Build creator payload
    creator_data = await _build_creator_payload(current_user.id, creator, db)

    # Fetch all brand profiles
    brands_result = await db.execute(select(BrandProfile))
    brands = brands_result.scalars().all()

    if not brands:
        return BrandDealsResponse(opportunities=[], total=0)

    # Generate anonymous opportunities for each brand
    opportunities = []
    engine = AnonymousOpportunityEngine()

    for i, brand in enumerate(brands):
        brand_data = _build_brand_payload(brand)

        try:
            opp = engine.generate_opportunity(brand_data, creator_data)
            opportunities.append(BrandDealOpportunity(
                opportunity_id=opp.get("opportunity_id", ""),
                fit_level=opp.get("fit_level"),
                industry_hint=opp.get("industry_hint"),
                campaign_type=opp.get("campaign_type"),
                campaign_requirements=opp.get("campaign_requirements") if isinstance(opp.get("campaign_requirements"), str) else json.dumps(opp.get("campaign_requirements", "")),
                compensation=opp.get("compensation") if isinstance(opp.get("compensation"), str) else json.dumps(opp.get("compensation", "")),
                timeline=opp.get("timeline") if isinstance(opp.get("timeline"), str) else json.dumps(opp.get("timeline", "")),
                deliverables=opp.get("deliverables", []) if isinstance(opp.get("deliverables"), list) else [str(opp.get("deliverables", ""))],
                status=opp.get("status", "open"),
            ))
        except Exception as e:
            print(f"⚠️ Failed to generate opportunity for brand {brand.brand_name}: {e}")
            continue

        # Throttle: wait 2s between Gemini calls to stay under free-tier RPM
        if i < len(brands) - 1:
            await asyncio.sleep(2)

    return BrandDealsResponse(
        opportunities=opportunities,
        total=len(opportunities),
    )
