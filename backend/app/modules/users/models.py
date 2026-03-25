from sqlalchemy import String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import List, Optional
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str | None]
    role: Mapped[str] = mapped_column(String)  # BRAND | INFLUENCER | ADMIN
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    instagram_username: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships cascading all data destruction if user is deleted
    creator_profile: Mapped[Optional["CreatorProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    brand_profile: Mapped[Optional["BrandProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    
    instagram_profiles: Mapped[List["InstagramProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    instagram_posts: Mapped[List["InstagramPost"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    youtube_channels: Mapped[List["YouTubeChannel"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    youtube_videos: Mapped[List["YouTubeVideo"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    saved_creators: Mapped[List["SavedCreator"]] = relationship(
        "SavedCreator",
        foreign_keys="[SavedCreator.brand_id]",
        back_populates="brand",
        cascade="all, delete-orphan"
    )

class CreatorProfile(Base):
    __tablename__ = "creator_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    full_name: Mapped[str] = mapped_column(String)
    location: Mapped[str] = mapped_column(String)

    primary_platform: Mapped[str] = mapped_column(String)  # Instagram | YouTube
    category: Mapped[str] = mapped_column(String)

    # Instagram
    instagram_username: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    instagram_profile_link: Mapped[str | None] = mapped_column(String, nullable=True)

    # YouTube
    youtube_username: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    youtube_profile_link: Mapped[str | None] = mapped_column(String, nullable=True)

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_completed: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="creator_profile")


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    brand_name: Mapped[str] = mapped_column(String)
    industry: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    campaign_goal: Mapped[str] = mapped_column(String, default="Awareness")  # Awareness | Sales | Engagement
    budget_range: Mapped[str] = mapped_column(String, default="Mid")  # Low | Mid | High
    target_location: Mapped[str | None] = mapped_column(String, nullable=True)
    target_languages: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string list
    platform_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string list

    is_completed: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="brand_profile")


class SavedCreator(Base):
    __tablename__ = "saved_creators"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    fit_level: Mapped[str] = mapped_column(String)  # High | Medium | Low
    score_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string list
    
    saved_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brand: Mapped["User"] = relationship("User", foreign_keys=[brand_id], back_populates="saved_creators")
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
