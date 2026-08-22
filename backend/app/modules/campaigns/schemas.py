from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class CampaignCreate(BaseModel):
    """
    What a brand states about a campaign.

    Everything commercial here is supplied by the brand. That is the whole point
    of the entity: the AI previously had only a budget *band* to work from and
    invented a fee, a timeline and a deliverables list, which the creator's
    screen then presented as an offer.
    """

    name: str = Field(min_length=1, max_length=120)
    niche: str = Field(min_length=1, max_length=60)

    campaign_goal: str = "Awareness"          # Awareness | Sales | Engagement
    campaign_type: str = "Sponsored Post"

    #: Real money per creator. Optional so a brand can publish a brief first and
    #: add the fee once decided — but while it is absent the opportunity says so
    #: rather than guessing.
    budget_per_creator: int | None = Field(default=None, ge=0)
    currency: str = "INR"

    deliverables: list[str] | None = None
    deadline: date | None = None
    brief: str | None = None

    platform_preferences: list[str] | None = None
    target_location: str | None = None
    min_followers: int | None = Field(default=None, ge=0)
    creators_needed: int | None = Field(default=None, ge=1)

    is_open_to_applications: bool = True

    @field_validator("campaign_goal")
    @classmethod
    def _known_goal(cls, v: str) -> str:
        allowed = {"Awareness", "Sales", "Engagement"}
        if v not in allowed:
            raise ValueError(f"campaign_goal must be one of {sorted(allowed)}")
        return v


class CampaignUpdate(CampaignCreate):
    """Same shape; status may also be changed."""
    status: str | None = None

    @field_validator("status")
    @classmethod
    def _known_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"draft", "active", "closed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v


class CampaignResponse(BaseModel):
    """A campaign as its owning brand sees it."""

    id: int
    name: str
    status: str
    niche: str
    campaign_goal: str
    campaign_type: str
    budget_per_creator: int | None = None
    currency: str
    deliverables: list[str] | None = None
    deadline: date | None = None
    brief: str | None = None
    platform_preferences: list[str] | None = None
    target_location: str | None = None
    min_followers: int | None = None
    creators_needed: int | None = None
    is_open_to_applications: bool
    created_at: datetime
    #: How many creators have raised their hand for this campaign.
    interested_count: int = 0
