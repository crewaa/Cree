from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.common.dependencies import get_current_user, get_db
from app.modules.users.schemas import (
    UserResponse, CreatorProfileCreate, CreatorProfileResponse,
    BrandProfileCreate, BrandProfileResponse, SavedCreatorResponse
)
from app.modules.users.models import User, CreatorProfile, BrandProfile, SavedCreator
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.service import create_creator_profile, create_brand_profile
from app.modules.instagram.services.instagram_scrapper import scrape_and_store
from app.modules.youtube.service import scrape_and_store_youtube
from app.modules.users.completeness import brand_completeness, creator_completeness
from sqlalchemy import select


router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile-status")
async def profile_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Whether the caller has completed the profile their studio needs.

    Exists so the frontend can gate features without probing
    `/users/creator-profile` and catching a 404 — that worked, but logged a
    console error on every dashboard load, which reads as a broken app to
    anyone with devtools open.
    """
    if current_user.role == "INFLUENCER":
        profile = (await db.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == current_user.id)
        )).scalar()
        status = creator_completeness(profile)
        return {
            "has_profile": profile is not None,
            # Analytics need at least one linked platform to have anything to show.
            "has_social_handles": bool(
                profile and (profile.instagram_username or profile.youtube_username)
            ),
            # Same rule the admin console reports against, so the two can never
            # disagree about whether a given profile is finished.
            "is_complete": status.complete,
            "missing": status.missing,
        }

    if current_user.role == "BRAND":
        profile = (await db.execute(
            select(BrandProfile).where(BrandProfile.user_id == current_user.id)
        )).scalar()
        status = brand_completeness(profile)
        return {
            "has_profile": profile is not None,
            "has_social_handles": False,
            "is_complete": status.complete,
            "missing": status.missing,
        }

    # Admins have no studio profile to complete.
    return {"has_profile": True, "has_social_handles": True}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post(
    "/creator-profile",
    response_model=CreatorProfileResponse,
)
async def complete_creator_profile(
    data: CreatorProfileCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only influencers can complete this profile")

    profile = await create_creator_profile(
        db,
        current_user.id,
        data,
    )

    # Auto-trigger scraping for whichever platforms the creator supplied.
    # Both tasks open their own DB session; current_user.id is the correct key
    # (the scrape routes are keyed on users.id, not creator_profiles.id).
    if data.instagram_username:
        background_tasks.add_task(scrape_and_store, current_user.id)
    if data.youtube_username:
        background_tasks.add_task(scrape_and_store_youtube, current_user.id)

    return profile


@router.get(
    "/creator-profile",
    response_model=CreatorProfileResponse,
)
async def get_creator_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only influencers can access this")

    result = await db.execute(
        select(CreatorProfile).where(
            CreatorProfile.user_id == current_user.id
        )
    )
    profile = result.scalar()

    if not profile:
        raise HTTPException(404, "Profile not found")

    return profile


# NOTE: `GET /creator-profile/{user_id}` and `PUT /creator-profile/{user_id}`
# were removed during the security hardening pass. Both took no authentication
# dependency, so any anonymous caller could read — and, via the PUT, overwrite —
# any creator's profile, including their Instagram handle (which also redirects
# scraping). Neither had a live frontend consumer: the only caller was
# components/dashboard/creator-profile-form.tsx, reachable solely through
# dashboard/creator-dashboard.tsx, which is not routed anywhere.
#
# Authenticated equivalents already exist below and cover the same use case:
#   GET  /users/creator-profile   (own profile)
#   PUT  /users/creator-profile   (own profile)
# Admins can read any creator's profile via GET /admin/users/{id}.


@router.put(
    "/creator-profile",
    response_model=CreatorProfileResponse,
)
async def update_creator_profile(
    data: CreatorProfileCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "INFLUENCER":
        raise HTTPException(403, "Only influencers can update this")

    result = await db.execute(
        select(CreatorProfile).where(
            CreatorProfile.user_id == current_user.id
        )
    )
    profile = result.scalar()

    if not profile:
        raise HTTPException(404, "Profile not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    # Auto-trigger scraping for whichever platforms the creator supplied.
    if data.instagram_username:
        background_tasks.add_task(scrape_and_store, current_user.id)
    if data.youtube_username:
        background_tasks.add_task(scrape_and_store_youtube, current_user.id)

    return profile


# =====================
# Brand Profile CRUD
# =====================

@router.post(
    "/brand-profile",
    response_model=BrandProfileResponse,
)
async def complete_brand_profile(
    data: BrandProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "BRAND":
        raise HTTPException(403, "Only brands can complete this profile")

    return await create_brand_profile(
        db,
        current_user.id,
        data,
    )


@router.get(
    "/brand-profile",
    response_model=BrandProfileResponse,
)
async def get_brand_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "BRAND":
        raise HTTPException(403, "Only brands can access this")

    result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.user_id == current_user.id
        )
    )
    profile = result.scalar()

    if not profile:
        raise HTTPException(404, "Brand profile not found")

    return profile


@router.put(
    "/brand-profile",
    response_model=BrandProfileResponse,
)
async def update_brand_profile(
    data: BrandProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "BRAND":
        raise HTTPException(403, "Only brands can update this")

    result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.user_id == current_user.id
        )
    )
    profile = result.scalar()

    if not profile:
        raise HTTPException(404, "Brand profile not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


# =====================
# Saved Creators
# =====================

@router.get(
    "/saved-creators",
    response_model=list[SavedCreatorResponse],
)
async def get_saved_creators(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "BRAND":
        raise HTTPException(403, "Only brands can access saved creators")

    # Fetch saved creators with their basic creator details
    result = await db.execute(
        select(SavedCreator, CreatorProfile)
        .join(CreatorProfile, CreatorProfile.user_id == SavedCreator.creator_id)
        .where(SavedCreator.brand_id == current_user.id)
        .order_by(SavedCreator.saved_at.desc())
    )
    
    rows = result.all()
    
    response = []
    for saved, profile in rows:
        response.append(SavedCreatorResponse(
            id=saved.id,
            brand_id=saved.brand_id,
            creator_id=saved.creator_id,
            fit_level=saved.fit_level,
            score_reasoning=saved.score_reasoning,
            saved_at=saved.saved_at,
            creator_name=profile.full_name,
            creator_category=profile.category,
            creator_platform=profile.primary_platform,
        ))
        
    return response
