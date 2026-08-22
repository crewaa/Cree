from sqlalchemy import JSON, String, Boolean, ForeignKey, Text, DateTime, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import List, Optional
from app.core.database import Base

#: JSONB on PostgreSQL (queryable, indexable), plain JSON everywhere else.
#: The test suite runs on SQLite, which has no JSONB, so a bare JSONB column
#: would make the whole suite unrunnable to gain a production-only feature.
JSON_COLUMN = JSON().with_variant(JSONB, "postgresql")

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str | None]
    role: Mapped[str] = mapped_column(String)  # BRAND | INFLUENCER | ADMIN
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    instagram_username: Mapped[str | None] = mapped_column(String, nullable=True)

    # CURRENT_TIMESTAMP, not now(): portable across PostgreSQL and SQLite,
    # same convention as SavedCreator.saved_at.
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    # Relationships cascading all data destruction if user is deleted
    creator_profile: Mapped[Optional["CreatorProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    brand_profile: Mapped[Optional["BrandProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    
    instagram_profiles: Mapped[List["InstagramProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    instagram_posts: Mapped[List["InstagramPost"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    youtube_channels: Mapped[List["YouTubeChannel"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    youtube_videos: Mapped[List["YouTubeVideo"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    scrape_jobs: Mapped[List["ScrapeJob"]] = relationship(back_populates="user", cascade="all, delete-orphan")

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

    # Persistence for AI Tools.
    #
    # JSON, not TEXT. These held JSON-encoded strings, so answering "how many
    # creators were matched to Fitness campaigns" meant pulling every row into
    # Python and parsing it. `JSONB` on PostgreSQL is queryable and indexable;
    # the variant keeps plain `JSON` on SQLite so the tests still run.
    ai_summary: Mapped[dict | None] = mapped_column(JSON_COLUMN, nullable=True)
    summary_generated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cached_brand_deals: Mapped[list | None] = mapped_column(JSON_COLUMN, nullable=True)
    brand_deals_generated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #: DEPRECATED and unread. Defaults to True and is never set to False, so it
    #: never carried information. Completeness is computed from real fields in
    #: `app/modules/users/completeness.py`. Kept only because dropping a column
    #: from a live table is a bigger risk than an unused one; delete it in a
    #: deliberate migration if it ever gets in the way.
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

    #: DEPRECATED and unread. Defaults to True and is never set to False, so it
    #: never carried information. Completeness is computed from real fields in
    #: `app/modules/users/completeness.py`. Kept only because dropping a column
    #: from a live table is a bigger risk than an unused one; delete it in a
    #: deliberate migration if it ever gets in the way.
    is_completed: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="brand_profile")


class SavedCreator(Base):
    __tablename__ = "saved_creators"

    # A brand can hold at most one row per creator. Previously enforced only in
    # Python (ai/router.py pre-loads existing rows into a dict), which races when
    # the same brand runs discovery twice concurrently. Added in migration
    # b7e4c1a90f22.
    __table_args__ = (
        UniqueConstraint("brand_id", "creator_id", name="uq_saved_creators_brand_creator"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    fit_level: Mapped[str] = mapped_column(String)  # High | Medium | Low
    score_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string list
    
    # CURRENT_TIMESTAMP rather than func.now(): the latter compiles to a literal
    # `now()` in the DDL, which PostgreSQL understands but SQLite does not, so
    # any insert against a migration-built SQLite database failed with
    # "unknown function: now()". CURRENT_TIMESTAMP is standard SQL and works on
    # both, which keeps the test/CI database faithful to production.
    saved_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    brand: Mapped["User"] = relationship("User", foreign_keys=[brand_id], back_populates="saved_creators")
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
