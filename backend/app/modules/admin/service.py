from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException

from app.modules.users.completeness import brand_completeness, creator_completeness
from app.modules.users.models import User, CreatorProfile, BrandProfile
from app.modules.auth.service import signup_user
from app.modules.admin.schemas import (
    PlatformStats, AdminUserListItem, AdminUserDetail,
    PaginatedUsers,
)


async def get_platform_stats(db: AsyncSession) -> PlatformStats:
    """Aggregate counts by role."""
    total = await db.scalar(select(func.count(User.id)))
    creators = await db.scalar(
        select(func.count(User.id)).where(User.role == "INFLUENCER")
    )
    brands = await db.scalar(
        select(func.count(User.id)).where(User.role == "BRAND")
    )
    admins = await db.scalar(
        select(func.count(User.id)).where(User.role == "ADMIN")
    )
    since = datetime.now(timezone.utc) - timedelta(days=7)
    new_users = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= since)
    )

    return PlatformStats(
        total_users=total or 0,
        total_creators=creators or 0,
        total_brands=brands or 0,
        total_admins=admins or 0,
        new_users_last_7_days=new_users or 0,
    )


async def list_users(
    db: AsyncSession,
    role_filter: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedUsers:
    """Paginated, filterable user list."""
    # Clamp pagination. Previously unvalidated: page=0 produced a negative
    # OFFSET and a database error, and page_size was unbounded so a single
    # request could ask for the entire user table.
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = select(User)

    if role_filter:
        query = query.where(User.role == role_filter.upper())
    if search:
        conditions = [User.email.ilike(f"%{search}%")]
        if search.isdigit():
            conditions.append(User.id == int(search))
        query = query.where(or_(*conditions))

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(User.id.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    # Profile existence, batched instead of one query per user: two IN
    # queries for the whole page rather than up to `page_size` COUNT queries.
    creator_ids = [u.id for u in users if u.role == "INFLUENCER"]
    brand_ids = [u.id for u in users if u.role == "BRAND"]

    creators_with_profile: set[int] = set()
    if creator_ids:
        result = await db.execute(
            select(CreatorProfile.user_id).where(CreatorProfile.user_id.in_(creator_ids))
        )
        creators_with_profile = set(result.scalars().all())

    brands_with_profile: set[int] = set()
    if brand_ids:
        result = await db.execute(
            select(BrandProfile.user_id).where(BrandProfile.user_id.in_(brand_ids))
        )
        brands_with_profile = set(result.scalars().all())

    items = []
    for u in users:
        if u.role == "INFLUENCER":
            has_profile = u.id in creators_with_profile
        elif u.role == "BRAND":
            has_profile = u.id in brands_with_profile
        else:
            has_profile = False

        items.append(AdminUserListItem(
            id=u.id,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            has_profile=has_profile,
            created_at=u.created_at,
        ))

    return PaginatedUsers(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_user_detail(db: AsyncSession, user_id: int) -> AdminUserDetail:
    """Full user detail including profile data."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()

    if not user:
        raise HTTPException(404, "User not found")

    detail = AdminUserDetail(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )

    if user.role == "INFLUENCER":
        cp_result = await db.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == user_id)
        )
        cp = cp_result.scalar()
        if cp:
            detail.creator_full_name = cp.full_name
            detail.creator_location = cp.location
            detail.creator_category = cp.category
            detail.creator_primary_platform = cp.primary_platform
            detail.creator_instagram_username = cp.instagram_username
            detail.creator_youtube_username = cp.youtube_username
            detail.creator_bio = cp.bio
            # Computed, not read from `is_completed` — that column defaults to
            # True and is never set to False, so it always claimed complete.
            status = creator_completeness(cp)
            detail.creator_profile_completed = status.complete
            detail.creator_profile_missing = status.missing

    elif user.role == "BRAND":
        bp_result = await db.execute(
            select(BrandProfile).where(BrandProfile.user_id == user_id)
        )
        bp = bp_result.scalar()
        if bp:
            detail.brand_name = bp.brand_name
            detail.brand_industry = bp.industry
            detail.brand_description = bp.description
            detail.brand_website = bp.website
            detail.brand_campaign_goal = bp.campaign_goal
            detail.brand_budget_range = bp.budget_range
            status = brand_completeness(bp)
            detail.brand_profile_completed = status.complete
            detail.brand_profile_missing = status.missing

    return detail


async def delete_user(db: AsyncSession, user_id: int) -> None:
    """Delete user and cascade all related data."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()

    if not user:
        raise HTTPException(404, "User not found")

    if user.role == "ADMIN":
        raise HTTPException(400, "Cannot delete an admin user from the dashboard")

    await db.delete(user)
    await db.commit()


async def admin_create_user(
    db: AsyncSession,
    email: str,
    password: str,
    role: str,
) -> User:
    """
    Admin-initiated user creation (creators & brands only).

    Delegates to the same `signup_user` the public route uses. It previously had
    its own copy of the logic, which meant it kept all three bugs that were
    fixed on the signup path: bcrypt run inline (freezing the worker), no email
    normalisation (so an admin could create the duplicate-casing account that
    the public route now refuses), and no handling for a lost insert race.

    Two ways to create a user is two behaviours to keep in step, and this is
    what that costs. One definition, used by both.
    """
    if role.upper() not in ("BRAND", "INFLUENCER"):
        raise HTTPException(400, "Can only create BRAND or INFLUENCER users")

    return await signup_user(db, email, password, role)
