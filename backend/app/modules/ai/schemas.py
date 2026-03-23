from pydantic import BaseModel
from typing import List, Optional


class DiscoverCreatorsRequest(BaseModel):
    """Brand submits campaign requirements to discover matching creators."""
    niche: str
    budget_range: str = "Mid"  # Low | Mid | High
    campaign_goal: str = "Awareness"  # Awareness | Sales | Engagement
    target_location: str | None = None
    target_languages: list[str] | None = None
    platform_preferences: list[str] | None = None


class RankedCreator(BaseModel):
    creator_id: str
    creator_name: str | None = None
    fit_level: str
    score_reasoning: list[str] | None = None
    risks: list[str] | None = None
    recommended_campaign_type: str | None = None


class DiscoverCreatorsResponse(BaseModel):
    ranked_creators: list[RankedCreator]
    final_recommendation: str | None = None


class BrandDealOpportunity(BaseModel):
    opportunity_id: str
    fit_level: str | None = None
    industry_hint: str | None = None
    campaign_type: str | None = None
    campaign_requirements: str | None = None
    compensation: str | None = None
    timeline: str | None = None
    deliverables: list[str] | None = None
    status: str | None = "open"


class BrandDealsResponse(BaseModel):
    opportunities: list[BrandDealOpportunity]
    total: int
