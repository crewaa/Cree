from pydantic import BaseModel, EmailStr

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str

    class Config:
        from_attributes = True

class CreatorProfileCreate(BaseModel):
    full_name: str
    location: str
    primary_platform: str
    category: str
    instagram_username: str | None = None
    instagram_profile_link: str | None = None
    youtube_username: str | None = None
    youtube_profile_link: str | None = None
    bio: str | None = None

class CreatorProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    location: str
    primary_platform: str
    category: str
    instagram_username: str | None
    instagram_profile_link: str | None
    youtube_username: str | None
    youtube_profile_link: str | None
    bio: str | None

    class Config:
        from_attributes = True

class BrandProfileCreate(BaseModel):
    brand_name: str
    industry: str
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    campaign_goal: str = "Awareness"
    budget_range: str = "Mid"
    target_location: str | None = None
    target_languages: str | None = None  # JSON string
    platform_preferences: str | None = None  # JSON string

class BrandProfileResponse(BaseModel):
    id: int
    user_id: int
    brand_name: str
    industry: str
    description: str | None
    website: str | None
    logo_url: str | None
    campaign_goal: str
    budget_range: str
    target_location: str | None
    target_languages: str | None
    platform_preferences: str | None

    class Config:
        from_attributes = True
