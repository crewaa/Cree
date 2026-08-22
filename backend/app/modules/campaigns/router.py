"""
Campaign CRUD, scoped to the owning brand.

Every route resolves the campaign through `brand_id == current_user.id`, so a
brand can never read or modify another brand's campaign — the lookup simply
returns nothing. That is deliberate: an explicit ownership check that can be
forgotten is how the unauthenticated profile routes happened.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_db, get_current_user
from app.core.logging import logger
from app.modules.campaigns.models import Campaign, CampaignStatus
from app.modules.campaigns.schemas import (
    CampaignCreate, CampaignResponse, CampaignUpdate,
)
from app.modules.deals.models import InterestStatus, OpportunityInterest
from app.modules.users.models import User

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _dump_list(value: list[str] | None) -> str | None:
    """Store lists as JSON text, matching the existing brand_profiles convention."""
    return json.dumps(value) if value else None


def _load_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _to_response(campaign: Campaign, interested_count: int = 0) -> CampaignResponse:
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        niche=campaign.niche,
        campaign_goal=campaign.campaign_goal,
        campaign_type=campaign.campaign_type,
        budget_per_creator=campaign.budget_per_creator,
        currency=campaign.currency,
        deliverables=_load_list(campaign.deliverables),
        deadline=campaign.deadline,
        brief=campaign.brief,
        platform_preferences=_load_list(campaign.platform_preferences),
        target_location=campaign.target_location,
        min_followers=campaign.min_followers,
        creators_needed=campaign.creators_needed,
        is_open_to_applications=campaign.is_open_to_applications,
        created_at=campaign.created_at,
        interested_count=interested_count,
    )


async def _owned_campaign(db: AsyncSession, brand_id: int, campaign_id: int) -> Campaign:
    campaign = (await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.brand_id == brand_id,
        )
    )).scalar()

    if campaign is None:
        # 404 rather than 403 so the existence of another brand's campaign is
        # not disclosed.
        raise HTTPException(404, "Campaign not found")

    return campaign


def _require_brand(current_user: User) -> None:
    if current_user.role != "BRAND":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only brands can manage campaigns")


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a campaign with the brand's real terms."""
    _require_brand(current_user)

    campaign = Campaign(
        brand_id=current_user.id,
        name=data.name,
        status=CampaignStatus.ACTIVE,
        niche=data.niche,
        campaign_goal=data.campaign_goal,
        campaign_type=data.campaign_type,
        budget_per_creator=data.budget_per_creator,
        currency=data.currency,
        deliverables=_dump_list(data.deliverables),
        deadline=data.deadline,
        brief=data.brief,
        platform_preferences=_dump_list(data.platform_preferences),
        target_location=data.target_location,
        min_followers=data.min_followers,
        creators_needed=data.creators_needed,
        is_open_to_applications=data.is_open_to_applications,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    logger.info("Brand {} created campaign {}", current_user.id, campaign.id)
    return _to_response(campaign)


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """This brand's campaigns, newest first, with response counts."""
    _require_brand(current_user)

    campaigns = list((await db.execute(
        select(Campaign)
        .where(Campaign.brand_id == current_user.id)
        .order_by(Campaign.created_at.desc(), Campaign.id.desc())
    )).scalars().all())

    if not campaigns:
        return []

    # One grouped query rather than one per campaign.
    counts = dict((await db.execute(
        select(OpportunityInterest.campaign_id, func.count(OpportunityInterest.id))
        .where(
            OpportunityInterest.brand_id == current_user.id,
            OpportunityInterest.status == InterestStatus.INTERESTED,
            OpportunityInterest.campaign_id.isnot(None),
        )
        .group_by(OpportunityInterest.campaign_id)
    )).all())

    return [_to_response(c, counts.get(c.id, 0)) for c in campaigns]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_brand(current_user)
    campaign = await _owned_campaign(db, current_user.id, campaign_id)

    count = (await db.execute(
        select(func.count(OpportunityInterest.id)).where(
            OpportunityInterest.campaign_id == campaign_id,
            OpportunityInterest.status == InterestStatus.INTERESTED,
        )
    )).scalar() or 0

    return _to_response(campaign, count)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_brand(current_user)
    campaign = await _owned_campaign(db, current_user.id, campaign_id)

    campaign.name = data.name
    campaign.niche = data.niche
    campaign.campaign_goal = data.campaign_goal
    campaign.campaign_type = data.campaign_type
    campaign.budget_per_creator = data.budget_per_creator
    campaign.currency = data.currency
    campaign.deliverables = _dump_list(data.deliverables)
    campaign.deadline = data.deadline
    campaign.brief = data.brief
    campaign.platform_preferences = _dump_list(data.platform_preferences)
    campaign.target_location = data.target_location
    campaign.min_followers = data.min_followers
    campaign.creators_needed = data.creators_needed
    campaign.is_open_to_applications = data.is_open_to_applications
    if data.status:
        campaign.status = data.status

    await db.commit()
    await db.refresh(campaign)
    return _to_response(campaign)


@router.delete("/{campaign_id}")
async def close_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Close a campaign rather than delete it.

    Creators may already have expressed interest, and those records reference
    the campaign — hard-deleting would destroy the history of an agreement
    people acted on.
    """
    _require_brand(current_user)
    campaign = await _owned_campaign(db, current_user.id, campaign_id)

    campaign.status = CampaignStatus.CLOSED
    campaign.is_open_to_applications = False
    await db.commit()

    return {"status": "closed", "campaign_id": campaign_id}
