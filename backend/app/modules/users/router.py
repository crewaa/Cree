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
from sqlalchemy import select


router = APIRouter(prefix="/users", tags=["Users"])

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

    # Auto-trigger Instagram scraping if username provided
    if data.instagram_username:
        background_tasks.add_task(scrape_and_store, current_user.id)

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


@router.get(
    "/creator-profile/{user_id}",
    response_model=CreatorProfileResponse,
)
async def get_creator_profile_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreatorProfile).where(
            CreatorProfile.user_id == user_id
        )
    )
    profile = result.scalar()

    if not profile:
        raise HTTPException(404, "Profile not found")

    return profile


@router.put(
    "/creator-profile/{user_id}",
    response_model=CreatorProfileResponse,
)
async def update_creator_profile_by_id(
    user_id: int,
    data: CreatorProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreatorProfile).where(
            CreatorProfile.user_id == user_id
        )
    )
    profile = result.scalar()

    if not profile:
        raise HTTPException(404, "Profile not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


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

    # Auto-trigger Instagram scraping if username provided
    if data.instagram_username:
        background_tasks.add_task(scrape_and_store, current_user.id)

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
