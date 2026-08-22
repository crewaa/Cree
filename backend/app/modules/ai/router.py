"""
AI Routes - Discover Creators & Brand Deals
"""

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.common.dependencies import get_db, get_current_user
from app.common.rate_limit import rate_limit_user
from app.core.config import settings
from app.core.logging import logger
from app.modules.users.models import User, CreatorProfile, BrandProfile, SavedCreator
from app.modules.campaigns.models import Campaign, CampaignStatus
from app.modules.deals.models import InterestStatus, OpportunityInterest
from app.modules.instagram.models.instagram import InstagramProfile, InstagramPost
from app.modules.youtube.models import YouTubeChannel, YouTubeVideo
from app.modules.ai.schemas import (
    DiscoverCreatorsRequest,
    DiscoverCreatorsResponse,
    RankedCreator,
    BrandDealsResponse,
    BrandDealOpportunity,
    CreatorSummaryResponse,
    InterestRequest,
    InterestedCreator,
    InterestedCreatorsResponse,
)
from app.modules.ai.ai_service import (
    AnonymousOpportunityEngine,
    BrandCreatorRankingEngine,
    CampaignOpportunityEngine,
    CreatorAIEngine,
)

router = APIRouter(prefix="/ai", tags=["AI Engine"])


def _safe_json_parse(value: str | None) -> list:
    """Parse a JSON string list, return empty list if None or invalid."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


async def _build_creator_payloads(
    creators: list[CreatorProfile],
    db: AsyncSession,
) -> dict[int, dict]:
    """
    Build AI payloads for many creators using a fixed number of queries.

    The previous implementation ran four queries per creator inside a loop over
    every creator in the database (a 4N N+1). This issues four queries total,
    regardless of how many creators are involved, and groups in Python.
    """
    if not creators:
        return {}

    user_ids = [c.user_id for c in creators]

    ig_profiles = (await db.execute(
        select(InstagramProfile)
        .where(InstagramProfile.user_id.in_(user_ids))
        .order_by(InstagramProfile.scraped_at.desc())
    )).scalars().all()

    ig_posts = (await db.execute(
        select(InstagramPost)
        .where(InstagramPost.user_id.in_(user_ids))
        .order_by(InstagramPost.posted_at.desc())
    )).scalars().all()

    yt_channels = (await db.execute(
        select(YouTubeChannel)
        .where(YouTubeChannel.user_id.in_(user_ids))
        .order_by(YouTubeChannel.scraped_at.desc())
    )).scalars().all()

    yt_videos = (await db.execute(
        select(YouTubeVideo)
        .where(YouTubeVideo.user_id.in_(user_ids))
        .order_by(YouTubeVideo.published_at.desc())
    )).scalars().all()

    # Ordered desc, so the first entry per user is the newest snapshot.
    latest_ig: dict[int, InstagramProfile] = {}
    for p in ig_profiles:
        latest_ig.setdefault(p.user_id, p)

    latest_yt: dict[int, YouTubeChannel] = {}
    for c in yt_channels:
        latest_yt.setdefault(c.user_id, c)

    posts_by_user: dict[int, list] = defaultdict(list)
    for p in ig_posts:
        if len(posts_by_user[p.user_id]) < 10:
            posts_by_user[p.user_id].append(p)

    videos_by_user: dict[int, list] = defaultdict(list)
    for v in yt_videos:
        if len(videos_by_user[v.user_id]) < 10:
            videos_by_user[v.user_id].append(v)

    payloads: dict[int, dict] = {}

    for creator in creators:
        uid = creator.user_id
        ig_profile = latest_ig.get(uid)
        creator_posts = posts_by_user.get(uid, [])
        yt_channel = latest_yt.get(uid)
        creator_videos = videos_by_user.get(uid, [])

        platforms = []

        if ig_profile:
            avg_likes = avg_comments = 0
            if creator_posts:
                avg_likes = sum(p.likes or 0 for p in creator_posts) // len(creator_posts)
                avg_comments = sum(p.comments or 0 for p in creator_posts) // len(creator_posts)

            engagement_rate = 0
            if ig_profile.followers and ig_profile.followers > 0:
                engagement_rate = round(
                    (avg_likes + avg_comments) / ig_profile.followers * 100, 2
                )

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
                    for p in creator_posts[:5]
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
                    for v in creator_videos[:5]
                ],
            })

        payloads[uid] = {
            "creator_identity": {
                "id": str(uid),
                "name": creator.full_name,
                "primary_niche": creator.category,
                "location": creator.location,
                "pricing": "Mid",  # TODO: no real pricing model exists yet
            },
            "platforms": platforms,
        }

    return payloads


async def _build_creator_payload(user_id: int, creator: CreatorProfile, db: AsyncSession) -> dict:
    """Single-creator convenience wrapper around the batch builder."""
    payloads = await _build_creator_payloads([creator], db)
    return payloads[user_id]


def _staleness(generated_at) -> tuple[object, bool]:
    """
    Report when a cached AI result was produced and whether it is now stale.

    The `*_generated_at` columns existed from the start but were never read, so
    caches had no TTL and no staleness signal — a creator could act on analysis
    that predated a doubling of their follower count.
    """
    if generated_at is None:
        return None, False

    moment = generated_at
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - moment
    return generated_at, age.days >= settings.ai_cache_stale_after_days


def _headline_stats(payload: dict) -> dict:
    """
    Pull the numbers a brand needs to judge a creator out of the payload that
    was already assembled for the model — no extra queries.
    """
    stats: dict = {
        "avatar_url": None, "followers": None, "subscribers": None,
        "avg_likes": None, "avg_comments": None,
        "engagement_rate": None, "is_verified": None,
    }

    for platform in payload.get("platforms", []):
        if platform.get("platform") == "instagram":
            engagement = platform.get("engagement", {})
            stats["followers"] = platform.get("followers")
            stats["avg_likes"] = engagement.get("avg_likes")
            stats["avg_comments"] = engagement.get("avg_comments")
            stats["engagement_rate"] = engagement.get("engagement_rate")
            stats["is_verified"] = platform.get("verified")
        elif platform.get("platform") == "youtube":
            stats["subscribers"] = platform.get("subscribers")

    return stats


def _clears_follower_floor(payload: dict, minimum: int | None) -> bool:
    """
    Whether a creator meets a campaign's stated audience minimum.

    Reach is the larger of the two platform counts rather than their sum: a
    creator with 20k on Instagram and 20k on YouTube probably has substantial
    overlap, and adding them would let two small accounts fake one large one.

    A creator who has never run a scrape has no numbers at all. They pass. The
    alternative silently hides every new signup from every campaign that sets a
    floor, which is a worse failure than showing a brand someone it can skip.
    """
    if not minimum:
        return True

    stats = _headline_stats(payload)
    reach = max(stats.get("followers") or 0, stats.get("subscribers") or 0)
    return reach == 0 or reach >= minimum


def _build_campaign_payload(campaign: Campaign) -> dict:
    """
    Campaign data for the model.

    Includes the commercial terms so the model can judge fit against them, but
    the model is instructed not to restate them and the caller attaches the real
    values from this same record — so nothing a creator sees is model-authored.
    """
    return {
        "campaign": {
            "niche": campaign.niche,
            "goal": campaign.campaign_goal,
            "type": campaign.campaign_type,
            "budget_per_creator": campaign.budget_per_creator,
            "currency": campaign.currency,
            "deliverables": _safe_json_parse(campaign.deliverables),
            "deadline": str(campaign.deadline) if campaign.deadline else None,
            "brief": campaign.brief,
            "target_location": campaign.target_location,
            "min_followers": campaign.min_followers,
        },
        "platform_preferences": _safe_json_parse(campaign.platform_preferences) or ["instagram"],
    }


def _opportunity_from_campaign(campaign: Campaign, assessment: dict) -> BrandDealOpportunity:
    """
    Assemble what the creator sees.

    Every commercial value is read from the campaign record. The model supplies
    only fit, reasoning and a description — it cannot state a fee, so it cannot
    invent one. `terms_are_estimated` is False here precisely because a real
    brand typed these numbers.
    """
    deliverables = _safe_json_parse(campaign.deliverables)

    return BrandDealOpportunity(
        opportunity_id=str(uuid.uuid4()),
        # --- the brand's actual offer ---
        budget_per_creator=campaign.budget_per_creator,
        currency=campaign.currency,
        deadline=str(campaign.deadline) if campaign.deadline else None,
        deliverables=[str(d) for d in deliverables] or None,
        campaign_type=campaign.campaign_type,
        campaign_requirements=campaign.brief,
        terms_are_estimated=False,
        # --- the model's judgement ---
        fit_level=assessment.get("fit_level", "Medium"),
        industry_hint=assessment.get("industry_hint"),
        what_to_expect=assessment.get("what_to_expect"),
        why_it_fits=[str(r) for r in (assessment.get("why_it_fits") or [])] or None,
        status="open",
    )


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


def _decode_cached_deals(raw) -> list[dict]:
    """
    Read the cached deals, tolerating every shape this column has ever held.

    Three of them, and all three still exist in the wild:

    * a JSON **string** — every row written before the JSONB migration, plus
      SQLite, which round-trips JSON through text;
    * a bare **list of opportunity dicts** — the original format, before brand
      attribution was added;
    * the current **list of {"brand_id", "campaign_id", "opportunity"}** wrappers.

    Being liberal here is what stops a creator's Deals page going blank on the
    deploy that changes the format.
    """
    if not raw:
        return []

    data = raw
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return []
    if not isinstance(data, list):
        return []

    entries = []
    for item in data:
        if isinstance(item, dict) and "opportunity" in item:
            entries.append({
                "brand_id": item.get("brand_id"),
                "campaign_id": item.get("campaign_id"),
                "opportunity": item["opportunity"],
            })
        elif isinstance(item, dict):
            entries.append({"brand_id": None, "campaign_id": None, "opportunity": item})
    return entries


async def _public_opportunities(
    db: AsyncSession, creator_user_id: int, entries: list[dict]
) -> list[BrandDealOpportunity]:
    """
    Strip brand attribution and mark which opportunities the creator already
    raised their hand for. `brand_id` must never leave the server.
    """
    if not entries:
        return []

    ids = [e["opportunity"].get("opportunity_id") for e in entries]
    already = set((await db.execute(
        select(OpportunityInterest.opportunity_id).where(
            OpportunityInterest.creator_id == creator_user_id,
            OpportunityInterest.opportunity_id.in_([i for i in ids if i]),
            OpportunityInterest.status == InterestStatus.INTERESTED,
        )
    )).scalars().all())

    out = []
    for entry in entries:
        payload = dict(entry["opportunity"])
        # Belt and braces: neither attribution key may ever reach the creator.
        payload.pop("brand_id", None)
        payload.pop("campaign_id", None)
        opp = BrandDealOpportunity(**payload)
        opp.interested = opp.opportunity_id in already
        out.append(opp)
    return out


# =============================================================================
# Creator Summary - Influencer gets AI-generated profile analysis
# =============================================================================

@router.get("/creator-summary", response_model=CreatorSummaryResponse | None)
async def get_cached_creator_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the previously generated AI summary for the creator."""
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only creators can access the growth analyzer")

    creator_result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    creator = creator_result.scalar()
    
    if not creator or not creator.ai_summary:
        return None
        
    # The column is JSON now, so this is already a dict. Rows written before
    # the JSONB migration (and SQLite, which round-trips through text) can still
    # hand back a string, so both are accepted.
    data = creator.ai_summary
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(data, dict):
        return None
    data = dict(data)

    generated_at, is_stale = _staleness(creator.summary_generated_at)
    data.pop("generated_at", None)
    data.pop("is_stale", None)
    return CreatorSummaryResponse(**data, generated_at=generated_at, is_stale=is_stale)


@router.post(
    "/creator-summary",
    response_model=CreatorSummaryResponse,
    dependencies=[rate_limit_user(10, 3600, "ai_summary")],
)
async def generate_creator_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creator forces a new AI-generated summary and analysis of their profile."""
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only creators can access the growth analyzer")

    # Get creator profile
    creator_result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    creator = creator_result.scalar()

    if not creator:
        raise HTTPException(404, "Please complete your creator profile first")

    # Build creator payload with real platform data
    creator_payload = await _build_creator_payload(current_user.id, creator, db)

    # Run AI engine
    try:
        engine = CreatorAIEngine()
        result = await engine.generate_creator_profile(creator_payload)
    except RuntimeError:
        raise HTTPException(429, "AI Engine rate-limited. Please wait a minute and try again.")
    except Exception as e:
        logger.error("Creator summary failed for user {}: {}", current_user.id, e)
        raise HTTPException(500, "AI Engine error. Please try again.")

    response = CreatorSummaryResponse(
        creator_id=result.get("creator_id"),
        summary=result.get("summary"),
        strengths=result.get("strengths", []),
        improvement_areas=result.get("improvement_areas", []),
        best_brand_categories=result.get("best_brand_categories", []),
        recommended_content_formats=result.get("recommended_content_formats", []),
    )
    
    # Cache the result to prevent wiping on refresh
    creator.ai_summary = response.model_dump(mode="json")
    creator.summary_generated_at = datetime.now(timezone.utc)
    await db.commit()

    return response


# =============================================================================
# Discover Creators - Brand finds matching influencers
# =============================================================================

@router.post(
    "/discover-creators",
    response_model=DiscoverCreatorsResponse,
    dependencies=[rate_limit_user(20, 3600, "ai_discover")],
)
async def discover_creators(
    request: DiscoverCreatorsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rank creators for a brand's campaign.

    Criteria come from a saved campaign when one is given, and from the loose
    request fields otherwise. Resolving that first, into one set of locals, is
    deliberate: the alternative — reading `campaign.niche or request.niche` at
    each use site — is how a search ends up half-matching a campaign and half
    matching a stale form.
    """
    if current_user.role != "BRAND":
        raise HTTPException(403, "Only brands can discover creators")

    campaign: Campaign | None = None
    if request.campaign_id is not None:
        campaign = (await db.execute(
            select(Campaign).where(
                Campaign.id == request.campaign_id,
                Campaign.brand_id == current_user.id,
            )
        )).scalar()

        if campaign is None:
            # 404 rather than 403, matching /campaigns: another brand's campaign
            # must not be distinguishable from one that does not exist.
            raise HTTPException(404, "Campaign not found")

    if campaign is not None:
        niche = campaign.niche
        campaign_goal = campaign.campaign_goal
        target_location = campaign.target_location
        target_languages = None
        platform_preferences = _safe_json_parse(campaign.platform_preferences) or ["instagram"]
        min_followers = campaign.min_followers
    else:
        niche = (request.niche or "").strip()
        campaign_goal = request.campaign_goal
        target_location = request.target_location
        target_languages = request.target_languages
        platform_preferences = request.platform_preferences or ["instagram"]
        min_followers = None

    # Build brand data for the prompt.
    brand_data = {
        "brand_identity": {
            "brand_name": "Your Brand",  # replaced below if a profile exists
            "industry": niche,
            "campaign_goal": campaign_goal,
            "budget_range": request.budget_range,
            "target_location": target_location or "India",
            "target_languages": target_languages or ["English"],
        },
        "platform_preferences": platform_preferences,
    }

    if campaign is not None:
        # The brand is looking at its own campaign, so the real terms can go in.
        # (Contrast the creator-facing path, where they are stripped.) Giving the
        # model the actual fee lets it reason about affordability instead of
        # guessing from a Low/Mid/High band nobody set.
        brand_data["campaign"] = {
            "name": campaign.name,
            "type": campaign.campaign_type,
            "budget_per_creator": campaign.budget_per_creator,
            "currency": campaign.currency,
            "deliverables": _safe_json_parse(campaign.deliverables),
            "deadline": str(campaign.deadline) if campaign.deadline else None,
            "brief": campaign.brief,
            "min_followers": campaign.min_followers,
            "creators_needed": campaign.creators_needed,
        }

    # Also try to fetch brand profile to enrich data
    brand_profile_result = await db.execute(
        select(BrandProfile).where(BrandProfile.user_id == current_user.id)
    )
    brand_profile = brand_profile_result.scalar()

    if brand_profile:
        brand_data["brand_identity"]["brand_name"] = brand_profile.brand_name
        if not niche:
            brand_data["brand_identity"]["industry"] = brand_profile.industry

    # Narrow the candidate set in SQL before involving the model.
    #
    # This previously did `select(CreatorProfile)` with no filter and serialised
    # EVERY creator in the database into a single prompt, which breaks on the
    # context limit as the platform grows and makes ranking quality worse.
    creators_query = select(CreatorProfile)

    platforms = [p.lower() for p in platform_preferences]
    if platforms:
        platform_filters = []
        if "instagram" in platforms:
            platform_filters.append(CreatorProfile.instagram_username.isnot(None))
        if "youtube" in platforms:
            platform_filters.append(CreatorProfile.youtube_username.isnot(None))
        if platform_filters:
            creators_query = creators_query.where(or_(*platform_filters))

    # Rank by relevance before the model sees anything.
    #
    # The niche used to be passed to the prompt and nowhere else, so the
    # candidate set ignored it entirely: a Fitness campaign was observed
    # returning Food and Tech creators as "High fit" while the actual Fitness
    # creator was crowded out. `CreatorProfile.category` holds exactly the value
    # the brand picked from the niche selector.
    #
    # This orders rather than hard-filters, so a brand in a thin niche still
    # gets results instead of an empty screen — but same-niche creators are
    # always considered first and fill the prompt budget.
    ordering = []

    if niche:
        ordering.append((CreatorProfile.category == niche).desc())

    if target_location:
        # Location is free text and often blank, so it is a tiebreaker only.
        ordering.append((CreatorProfile.location == target_location).desc())

    ordering.append(CreatorProfile.id.desc())
    creators_query = creators_query.order_by(*ordering)

    # Follower counts live in the scrape snapshot tables, not on the profile, so
    # a floor cannot be applied in this query. Over-fetch instead, filter once
    # the payloads are built, then truncate — otherwise the SQL limit would cut
    # the pool down before the floor had a chance to remove anyone.
    fetch_limit = settings.ai_max_creators_per_prompt
    if min_followers:
        fetch_limit = min(fetch_limit * 3, 200)

    creators_query = creators_query.limit(fetch_limit)

    creators_result = await db.execute(creators_query)
    creators = list(creators_result.scalars().all())

    if not creators:
        return DiscoverCreatorsResponse(
            ranked_creators=[],
            final_recommendation=(
                "No creators match those campaign requirements yet. "
                "Try widening the platform or location filters."
            ),
            campaign_id=campaign.id if campaign else None,
            campaign_name=campaign.name if campaign else None,
            criteria_source="campaign" if campaign else "custom",
        )

    # One batched build for all candidates (4 queries total, not 4 per creator).
    payloads = await _build_creator_payloads(creators, db)

    follower_floor_relaxed = False
    if min_followers:
        clearing = [c for c in creators if _clears_follower_floor(payloads.get(c.user_id, {}), min_followers)]
        if clearing:
            creators = clearing
        else:
            # Every candidate is below the stated floor. Returning an empty
            # screen would be defensible, but the brand cannot tell an empty
            # result from a broken one — so return the ranking and say the floor
            # could not be met.
            follower_floor_relaxed = True

    creators = creators[: settings.ai_max_creators_per_prompt]
    creators_data = [payloads[c.user_id] for c in creators]

    # Used to attach verified profile data to whatever the model ranks.
    creators_by_id = {c.user_id: c for c in creators}

    # The set of creator ids we actually sent to the model. Anything the model
    # returns that is not in here is a hallucination and must not be persisted.
    valid_creator_ids = {creator.user_id for creator in creators}

    # Run AI ranking
    try:
        engine = BrandCreatorRankingEngine()
        result = await engine.rank_creators(brand_data, creators_data)
    except RuntimeError:
        # Rate limit / quota exceeded
        raise HTTPException(429, "AI Engine rate-limited. Please wait a minute and try again.")
    except Exception as e:
        # Log the detail server-side; do not echo raw upstream errors to the client.
        logger.error("Creator ranking failed for brand {}: {}", current_user.id, e)
        raise HTTPException(500, "AI Engine error. Please try again.")

    # Parse result
    ranked = []
    
    # Pre-fetch existing saved creators for this brand to upsert instead of duplicate
    saved_creators_result = await db.execute(
        select(SavedCreator).where(SavedCreator.brand_id == current_user.id)
    )
    existing_saved = {sc.creator_id: sc for sc in saved_creators_result.scalars().all()}
    
    for c in result.get("ranked_creators", []):
        c_id_str = c.get("creator_id", "unknown")
        if c_id_str == "unknown":
            continue

        # The model returns creator_id as a string. It may be non-numeric, or a
        # plausible-looking id that was never sent. Either would corrupt
        # saved_creators — a bad FK aborts the whole commit and loses the entire
        # discovery result, and a wrong-but-real id silently persists a false match.
        try:
            c_id_int = int(c_id_str)
        except (TypeError, ValueError):
            logger.warning("Model returned a non-numeric creator_id: {!r}", c_id_str)
            continue

        if c_id_int not in valid_creator_ids:
            logger.warning(
                "Model returned creator_id {} which was not in the request set; skipping",
                c_id_int,
            )
            continue

        fit_level = c.get("fit_level", "Low")
        reasoning = c.get("score_reasoning", [])

        # Facts come from the database; the model only supplies judgement.
        # Its `creator_name` is ignored in favour of the stored profile so a
        # hallucinated name can never be shown to a brand as real.
        profile = creators_by_id[c_id_int]
        stats = _headline_stats(payloads.get(c_id_int, {}))

        ranked.append(RankedCreator(
            creator_id=c_id_str,
            creator_name=profile.full_name,
            fit_level=fit_level,
            score_reasoning=reasoning,
            risks=c.get("risks", []),
            recommended_campaign_type=c.get("recommended_campaign_type"),
            category=profile.category,
            location=profile.location,
            primary_platform=profile.primary_platform,
            bio=profile.bio,
            instagram_username=profile.instagram_username,
            instagram_url=(
                profile.instagram_profile_link
                or (f"https://instagram.com/{profile.instagram_username}"
                    if profile.instagram_username else None)
            ),
            youtube_username=profile.youtube_username,
            youtube_url=(
                profile.youtube_profile_link
                or (f"https://youtube.com/@{profile.youtube_username}"
                    if profile.youtube_username else None)
            ),
            **stats,
        ))
        
        # Save or update the creator connection in the DB
        if c_id_int in existing_saved:
            existing = existing_saved[c_id_int]
            existing.fit_level = fit_level
            existing.score_reasoning = json.dumps(reasoning)
        else:
            new_saved = SavedCreator(
                brand_id=current_user.id,
                creator_id=c_id_int,
                fit_level=fit_level,
                score_reasoning=json.dumps(reasoning)
            )
            db.add(new_saved)
            
    await db.commit()

    recommendation = result.get("final_recommendation")
    if follower_floor_relaxed:
        note = (
            f"No creator currently clears the {min_followers:,}-follower minimum on this "
            "campaign, so the ranking below ignores it."
        )
        recommendation = f"{note} {recommendation}".strip() if recommendation else note

    return DiscoverCreatorsResponse(
        ranked_creators=ranked,
        final_recommendation=recommendation,
        campaign_id=campaign.id if campaign else None,
        campaign_name=campaign.name if campaign else None,
        criteria_source="campaign" if campaign else "custom",
        follower_floor_relaxed=follower_floor_relaxed,
    )


# =============================================================================
# Brand Deals - Influencer sees anonymous brand opportunities
# =============================================================================

@router.get("/brand-deals", response_model=BrandDealsResponse | None)
async def get_cached_brand_deals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve previously generated anonymous opportunities."""
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only influencers can view brand deals")

    creator_result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    creator = creator_result.scalar()
    
    if not creator or not creator.cached_brand_deals:
        return None
        
    entries = _decode_cached_deals(creator.cached_brand_deals)
    if not entries:
        return None

    opportunities = await _public_opportunities(db, current_user.id, entries)
    generated_at, is_stale = _staleness(creator.brand_deals_generated_at)
    return BrandDealsResponse(
        opportunities=opportunities,
        total=len(opportunities),
        generated_at=generated_at,
        is_stale=is_stale,
    )

async def _brand_deal_sources(
    db: AsyncSession, creator: CreatorProfile
) -> tuple[list[Campaign], list[BrandProfile]]:
    """
    Choose what to assess, most relevant first.

    Ordering by the creator's own niche is the mirror of the discovery fix: a
    Fitness creator was being shown whatever campaign happened to be newest,
    because the run was ordered by `created_at` alone. Since the concurrency
    semaphore hands out slots in list order, putting same-niche work first also
    means the first opportunities to *finish* are the most relevant ones — which
    is what the streaming endpoint shows first.

    This orders rather than filters. A creator in a thin niche still sees
    something instead of an empty screen.
    """
    campaign_order = []
    brand_order = []

    if creator.category:
        campaign_order.append((Campaign.niche == creator.category).desc())
        brand_order.append((BrandProfile.industry == creator.category).desc())

    campaign_order.append(Campaign.created_at.desc())
    brand_order.append(BrandProfile.id.desc())

    # A campaign carries the brand's actual fee, deliverables and deadline, so
    # the model never has to invent commercial terms. Brands that have not
    # created a campaign yet still appear, via the legacy profile-derived path,
    # but their terms are flagged as estimates.
    campaigns = list((await db.execute(
        select(Campaign)
        .where(
            Campaign.status == CampaignStatus.ACTIVE,
            Campaign.is_open_to_applications.is_(True),
        )
        .order_by(*campaign_order)
        .limit(settings.ai_max_brands_per_run)
    )).scalars().all())

    remaining = settings.ai_max_brands_per_run - len(campaigns)
    legacy_brands = []
    if remaining > 0:
        brand_ids_with_campaigns = {c.brand_id for c in campaigns}
        legacy_brands = [
            b for b in (await db.execute(
                select(BrandProfile).order_by(*brand_order).limit(remaining * 2)
            )).scalars().all()
            if b.user_id not in brand_ids_with_campaigns
        ][:remaining]

    return campaigns, legacy_brands


async def _assess_opportunities(
    campaigns: list[Campaign],
    legacy_brands: list[BrandProfile],
    creator_data: dict,
    creator_user_id: int,
):
    """
    Yield `(brand_id, campaign_id, opportunity)` as each assessment completes.

    One generator feeds both the batch endpoint and the streaming one, so the
    two can never drift on the thing that matters — the anonymity and
    real-terms handling below happens once, not once per endpoint.
    """
    semaphore = asyncio.Semaphore(settings.ai_max_concurrent_calls)
    campaign_engine = CampaignOpportunityEngine()
    legacy_engine = AnonymousOpportunityEngine()

    async def from_campaign(campaign: Campaign):
        """Real terms: the model judges fit, the database supplies the numbers."""
        async with semaphore:
            try:
                assessment = await campaign_engine.assess(
                    _build_campaign_payload(campaign), creator_data
                )
            except RuntimeError:
                raise
            except Exception as e:
                logger.warning("Assessment failed for campaign {}: {}", campaign.id, e)
                return None
        return (campaign.brand_id, campaign.id, _opportunity_from_campaign(campaign, assessment))

    async def from_profile(brand: BrandProfile):
        """Legacy path for brands with no campaign — terms remain estimates."""
        async with semaphore:
            try:
                opp = await legacy_engine.generate_opportunity(
                    _build_brand_payload(brand), creator_data
                )
            except RuntimeError:
                raise
            except Exception as e:
                logger.warning("Opportunity failed for brand {}: {}", brand.id, e)
                return None

        def as_text(value):
            if value is None or isinstance(value, str):
                return value
            return json.dumps(value)

        deliverables = opp.get("deliverables", [])
        if not isinstance(deliverables, list):
            deliverables = [str(deliverables)] if deliverables else []

        return (brand.user_id, None, BrandDealOpportunity(
            opportunity_id=opp.get("opportunity_id", ""),
            fit_level=opp.get("fit_level"),
            industry_hint=opp.get("industry_hint"),
            campaign_type=opp.get("campaign_type"),
            campaign_requirements=as_text(opp.get("campaign_requirements")),
            compensation=as_text(opp.get("compensation")),
            timeline=as_text(opp.get("timeline")),
            deliverables=[str(d) for d in deliverables],
            status=opp.get("status", "open"),
            budget_range=brand.budget_range,
            terms_are_estimated=True,
        ))

    tasks = [asyncio.create_task(from_campaign(c)) for c in campaigns]
    tasks += [asyncio.create_task(from_profile(b)) for b in legacy_brands]

    produced = 0
    try:
        for completed in asyncio.as_completed(tasks):
            result = await completed
            if result is not None:
                produced += 1
                yield result
    finally:
        # A client that disconnects mid-stream closes this generator. Without
        # this the remaining Gemini calls keep running and keep costing money
        # for a screen nobody is looking at.
        for task in tasks:
            if not task.done():
                task.cancel()

    failed = (len(campaigns) + len(legacy_brands)) - produced
    if failed:
        logger.warning(
            "{}/{} opportunities failed for user {}",
            failed, len(campaigns) + len(legacy_brands), creator_user_id,
        )


def _cache_entries(produced: list[tuple]) -> list[dict]:
    """
    Cache with brand AND campaign attribution so a later expression of interest
    can be routed to the right campaign. Both are stripped before anything
    reaches the creator.
    """
    return [
        {"brand_id": bid, "campaign_id": cid, "opportunity": opp.model_dump(mode="json")}
        for bid, cid, opp in produced
    ]


# Fans out to one Gemini call per brand, so this is the most expensive
# endpoint on the platform.
@router.post(
    "/brand-deals",
    response_model=BrandDealsResponse,
    dependencies=[rate_limit_user(6, 3600, "ai_deals")],
)
async def generate_brand_deals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Influencer generates a fresh batch of anonymous opportunities via AI."""
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only influencers can view brand deals")

    creator_result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )
    creator = creator_result.scalar()

    if not creator:
        raise HTTPException(404, "Please complete your creator profile first")

    creator_data = await _build_creator_payload(current_user.id, creator, db)
    campaigns, legacy_brands = await _brand_deal_sources(db, creator)

    if not campaigns and not legacy_brands:
        return BrandDealsResponse(opportunities=[], total=0)

    produced = []
    try:
        async for item in _assess_opportunities(
            campaigns, legacy_brands, creator_data, current_user.id
        ):
            produced.append(item)
    except RuntimeError:
        raise HTTPException(
            429, "AI Engine rate-limited. Please wait a minute and try again."
        )
    except Exception as e:
        logger.error("Brand deals generation failed for user {}: {}", current_user.id, e)
        raise HTTPException(500, "AI Engine error. Please try again.")

    entries = _cache_entries(produced)
    creator.cached_brand_deals = entries
    creator.brand_deals_generated_at = datetime.now(timezone.utc)
    await db.commit()

    public = await _public_opportunities(db, current_user.id, entries)

    return BrandDealsResponse(
        opportunities=public,
        total=len(public),
        generated_at=datetime.now(timezone.utc),
        is_stale=False,
    )


@router.post(
    "/brand-deals/stream",
    dependencies=[rate_limit_user(6, 3600, "ai_deals")],
)
async def stream_brand_deals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The same run as `POST /brand-deals`, emitted as NDJSON one card at a time.

    Waiting for the whole batch meant a creator stared at a spinner for the
    length of the *slowest* brand — 10-20 seconds — before seeing anything. Each
    line here is a complete opportunity, so the first card lands as soon as the
    first assessment returns.

    Line protocol, one JSON object per line:
      {"type": "opportunity", "opportunity": {...}}
      {"type": "done", "total": N, "generated_at": "..."}
      {"type": "error", "detail": "..."}

    The injected session is used inside the streaming body deliberately, and it
    was checked rather than assumed: on FastAPI 0.141 / Starlette 1.6 the
    dependency is finalised after the body is consumed, so reads and the final
    commit below both succeed. If FastAPI is ever upgraded and this route starts
    raising on a closed session, that contract changed — open a session from
    `AsyncSessionLocal` here instead.
    """
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only influencers can view brand deals")

    async def lines():
        try:
            creator = (await db.execute(
                select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
            )).scalar()

            if not creator:
                yield json.dumps({
                    "type": "error",
                    "detail": "Please complete your creator profile first",
                }) + "\n"
                return

            creator_data = await _build_creator_payload(current_user.id, creator, db)
            campaigns, legacy_brands = await _brand_deal_sources(db, creator)

            produced: list[tuple] = []
            try:
                async for item in _assess_opportunities(
                    campaigns, legacy_brands, creator_data, current_user.id
                ):
                    produced.append(item)
                    # Strip attribution per item, through the same helper the
                    # batch path uses — the creator must not learn the brand.
                    public = await _public_opportunities(
                        db, current_user.id, _cache_entries([item])
                    )
                    yield json.dumps({
                        "type": "opportunity",
                        "opportunity": public[0].model_dump(mode="json"),
                    }) + "\n"
            except RuntimeError:
                # Headers are long gone, so a 429 is no longer available.
                # Say so in-band instead of truncating silently.
                yield json.dumps({
                    "type": "error",
                    "detail": "AI Engine rate-limited. Please wait a minute and try again.",
                }) + "\n"
                return

            generated_at = datetime.now(timezone.utc)
            creator.cached_brand_deals = _cache_entries(produced)
            creator.brand_deals_generated_at = generated_at
            await db.commit()

            yield json.dumps({
                "type": "done",
                "total": len(produced),
                "generated_at": generated_at.isoformat(),
            }) + "\n"
        except asyncio.CancelledError:
            # The creator navigated away. Nothing to report to anyone.
            raise
        except Exception as e:
            logger.error("Brand deals stream failed for user {}: {}", current_user.id, e)
            yield json.dumps({
                "type": "error",
                "detail": "AI Engine error. Please try again.",
            }) + "\n"

    return StreamingResponse(
        lines(),
        media_type="application/x-ndjson",
        # Proxies that buffer would defeat the entire point of streaming.
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


# =============================================================================
# Expression of interest — the step that closes the marketplace loop
# =============================================================================

@router.post(
    "/opportunities/interest",
    dependencies=[rate_limit_user(60, 3600, "interest")],
)
async def express_interest(
    request: InterestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creator registers interest in an opportunity.

    The creator sends only the opportunity id — never a brand id, which they do
    not have and must not learn. The originating brand is resolved server-side
    from the creator's own cached deals, which is also what stops a creator
    registering interest in an opportunity that was never offered to them.
    """
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only creators can express interest")

    creator = (await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
    )).scalar()
    if not creator:
        raise HTTPException(404, "Please complete your creator profile first")

    entries = _decode_cached_deals(creator.cached_brand_deals)
    match = next(
        (e for e in entries
         if e["opportunity"].get("opportunity_id") == request.opportunity_id),
        None,
    )
    if match is None:
        raise HTTPException(404, "That opportunity is no longer available")

    if match.get("brand_id") is None:
        # Cached before brand attribution existed; regenerating repairs it.
        raise HTTPException(
            409,
            "This opportunity needs refreshing before you can apply. "
            "Please refresh your deals and try again.",
        )

    existing = (await db.execute(
        select(OpportunityInterest).where(
            OpportunityInterest.creator_id == current_user.id,
            OpportunityInterest.opportunity_id == request.opportunity_id,
        )
    )).scalar()

    if existing:
        existing.status = InterestStatus.INTERESTED
        existing.message = request.message
    else:
        db.add(OpportunityInterest(
            creator_id=current_user.id,
            brand_id=match["brand_id"],
            campaign_id=match.get("campaign_id"),
            opportunity_id=request.opportunity_id,
            status=InterestStatus.INTERESTED,
            opportunity_snapshot=json.dumps(match["opportunity"]),
            message=request.message,
        ))

    await db.commit()
    logger.info(
        "Creator {} expressed interest in opportunity {}",
        current_user.id, request.opportunity_id,
    )
    return {"status": "interested", "opportunity_id": request.opportunity_id}


@router.delete("/opportunities/interest/{opportunity_id}")
async def withdraw_interest(
    opportunity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creator withdraws interest. Kept as a status change for auditability."""
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only creators can withdraw interest")

    interest = (await db.execute(
        select(OpportunityInterest).where(
            OpportunityInterest.creator_id == current_user.id,
            OpportunityInterest.opportunity_id == opportunity_id,
        )
    )).scalar()

    if not interest:
        raise HTTPException(404, "No interest recorded for that opportunity")

    interest.status = InterestStatus.WITHDRAWN
    await db.commit()
    return {"status": "withdrawn", "opportunity_id": opportunity_id}


@router.get("/interested-creators", response_model=InterestedCreatorsResponse)
async def list_interested_creators(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creators who have raised their hand for this brand's opportunities.

    Contact details are included: the creator disclosed themselves by opting in.
    The reverse never happens — the brand's identity is not revealed to a
    creator at any point.
    """
    if current_user.role != "BRAND":
        raise HTTPException(403, "Only brands can view interested creators")

    rows = (await db.execute(
        select(OpportunityInterest, User, CreatorProfile)
        .join(User, User.id == OpportunityInterest.creator_id)
        .join(CreatorProfile, CreatorProfile.user_id == OpportunityInterest.creator_id)
        .where(
            OpportunityInterest.brand_id == current_user.id,
            OpportunityInterest.status == InterestStatus.INTERESTED,
        )
        .order_by(OpportunityInterest.created_at.desc())
    )).all()

    if not rows:
        return InterestedCreatorsResponse(creators=[], total=0)

    profiles = [profile for _, _, profile in rows]
    payloads = await _build_creator_payloads(profiles, db)

    creators = []
    for interest, user, profile in rows:
        stats = _headline_stats(payloads.get(profile.user_id, {}))
        try:
            snapshot = json.loads(interest.opportunity_snapshot or "{}")
        except (json.JSONDecodeError, TypeError):
            snapshot = {}
        campaign_type = snapshot.get("campaign_type") if isinstance(snapshot, dict) else None

        creators.append(InterestedCreator(
            interest_id=interest.id,
            creator_id=user.id,
            creator_name=profile.full_name,
            email=user.email,
            category=profile.category,
            location=profile.location,
            instagram_username=profile.instagram_username,
            youtube_username=profile.youtube_username,
            followers=stats.get("followers"),
            engagement_rate=stats.get("engagement_rate"),
            message=interest.message,
            campaign_type=campaign_type,
            created_at=interest.created_at,
        ))

    return InterestedCreatorsResponse(creators=creators, total=len(creators))
