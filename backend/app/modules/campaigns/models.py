"""
Campaigns — what a brand actually wants, in the brand's own words.

Before this existed, a brand described itself once on its profile (industry,
budget *band*, goal) and nothing more. That left the AI with nothing concrete to
show a creator, so it invented the commercial terms — fee, timeline,
deliverables — and the UI rendered them as though a brand had offered them.

A campaign holds the real numbers. The AI's job becomes matching and explaining
fit, never inventing terms. It also means a brand can run several campaigns at
once, which a single profile could never express.
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CampaignStatus:
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class Campaign(Base):
    __tablename__ = "campaigns"

    __table_args__ = (
        # Supports "this brand's campaigns, newest first" and the active-campaign
        # sweep that Brand Deals performs.
        Index("ix_campaigns_brand_status", "brand_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    #: Brand-facing label. Never shown to creators — it would identify the brand.
    name: Mapped[str] = mapped_column(String)

    status: Mapped[str] = mapped_column(String, default=CampaignStatus.ACTIVE)

    # --- What the brand is looking for ---
    niche: Mapped[str] = mapped_column(String)
    #: JSON-encoded list, matching the existing convention on brand_profiles.
    platform_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_location: Mapped[str | None] = mapped_column(String, nullable=True)
    min_followers: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- The actual offer. These replace the invented values. ---
    campaign_goal: Mapped[str] = mapped_column(String, default="Awareness")
    campaign_type: Mapped[str] = mapped_column(String, default="Sponsored Post")
    #: Real money the brand is offering per creator, in whole rupees.
    budget_per_creator: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="INR")
    #: JSON-encoded list of deliverables the brand actually wants.
    deliverables: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: When content is due. A real date, not "within 3 weeks".
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    #: Anything else the creator should know before applying.
    brief: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: How many creators the brand wants for this campaign.
    creators_needed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    #: Whether creators may see and apply to this campaign.
    is_open_to_applications: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    brand: Mapped["User"] = relationship("User", foreign_keys=[brand_id])
