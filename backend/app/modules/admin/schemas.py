from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class PlatformStats(BaseModel):
    total_users: int
    total_creators: int
    total_brands: int
    total_admins: int
    new_users_last_7_days: int

    class Config:
        from_attributes = True


class AdminUserListItem(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    has_profile: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserDetail(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime

    # Creator profile fields (if role == INFLUENCER)
    creator_full_name: Optional[str] = None
    creator_location: Optional[str] = None
    creator_category: Optional[str] = None
    creator_primary_platform: Optional[str] = None
    creator_instagram_username: Optional[str] = None
    creator_youtube_username: Optional[str] = None
    creator_bio: Optional[str] = None
    creator_profile_completed: bool = False
    #: What is missing, so the flag is actionable rather than just red.
    creator_profile_missing: list[str] = []

    # Brand profile fields (if role == BRAND)
    brand_name: Optional[str] = None
    brand_industry: Optional[str] = None
    brand_description: Optional[str] = None
    brand_website: Optional[str] = None
    brand_campaign_goal: Optional[str] = None
    brand_budget_range: Optional[str] = None
    brand_profile_completed: bool = False
    brand_profile_missing: list[str] = []

    class Config:
        from_attributes = True


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str  # BRAND | INFLUENCER


class PaginatedUsers(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    page_size: int

    class Config:
        from_attributes = True
