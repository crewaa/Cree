"""
Expressions of interest.

This is the step that turns Crewaa from a recommendation engine into a
marketplace. Before it existed, a creator could read a fully-formed opportunity
and do nothing with it, and a brand could rank creators and never contact one —
both sides stopped at the moment of value.

Anonymity is preserved in the direction that matters: the creator never learns
which brand an opportunity came from, but expressing interest reveals the
*creator* to the brand. That is the correct asymmetry — the creator is opting in
to being contacted.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InterestStatus:
    INTERESTED = "interested"
    WITHDRAWN = "withdrawn"


class OpportunityInterest(Base):
    __tablename__ = "opportunity_interests"

    __table_args__ = (
        # One standing record per creator/opportunity. Tapping twice updates
        # rather than duplicates.
        UniqueConstraint(
            "creator_id", "opportunity_id", name="uq_interest_creator_opportunity"
        ),
        Index("ix_opportunity_interests_brand_created", "brand_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    #: Resolved server-side from the creator's cached opportunities. The creator
    #: never sees or sends this — it is how the brand is reached without the
    #: brand ever being disclosed.
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    #: The uuid generated when the opportunity was produced.
    opportunity_id: Mapped[str] = mapped_column(String, index=True)

    #: The campaign this interest was against, when the opportunity came from a
    #: real campaign. Nullable because opportunities generated before campaigns
    #: existed had no campaign to point at.
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(String, default=InterestStatus.INTERESTED)

    #: What the creator actually saw when they expressed interest, captured so
    #: the brand and the creator are looking at the same terms later even though
    #: opportunities are regenerated on every run.
    opportunity_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Optional note from the creator to the brand.
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])
    brand: Mapped["User"] = relationship("User", foreign_keys=[brand_id])
