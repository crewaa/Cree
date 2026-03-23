from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.modules.users.models import CreatorProfile, BrandProfile
from app.modules.users.schemas import CreatorProfileCreate, BrandProfileCreate

async def create_creator_profile(
    db: AsyncSession,
    user_id: int,
    data: CreatorProfileCreate,
):
    result = await db.execute(
        select(CreatorProfile).where(CreatorProfile.user_id == user_id)
    )
    if result.scalar():
        raise HTTPException(400, "Profile already exists")

    profile = CreatorProfile(
        user_id=user_id,
        **data.dict()
    )

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def create_brand_profile(
    db: AsyncSession,
    user_id: int,
    data: BrandProfileCreate,
):
    result = await db.execute(
        select(BrandProfile).where(BrandProfile.user_id == user_id)
    )
    if result.scalar():
        raise HTTPException(400, "Brand profile already exists")

    profile = BrandProfile(
        user_id=user_id,
        **data.dict()
    )

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
