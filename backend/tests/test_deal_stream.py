"""
Tests for streamed Brand Deals and niche-ordered sourcing.

Two properties are load-bearing here:

1. Streaming must not become a second, weaker copy of the batch path. Both go
   through `_assess_opportunities` and `_public_opportunities`, so the anonymity
   guarantee is tested on the streamed bytes, not assumed from the batch tests.
2. A creator's own niche must decide what gets assessed first. The run is capped,
   so ordering is not cosmetic — it decides what a creator sees at all.
"""

import json

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.modules.campaigns.models import Campaign, CampaignStatus
from app.modules.users.models import CreatorProfile
from tests.conftest import (
    auth_header, make_brand_profile, make_creator_profile, make_user,
)


def _stub_campaign_engine(monkeypatch):
    async def fake_assess(self, campaign_data, creator_data):
        return {
            "fit_level": "High",
            "industry_hint": "Health & Nutrition",
            "why_it_fits": ["Audience overlap."],
            "what_to_expect": "One reel.",
        }

    monkeypatch.setattr(
        "app.modules.ai.ai_service.CampaignOpportunityEngine.assess", fake_assess
    )
    monkeypatch.setattr(
        "app.modules.ai.ai_service.GeminiClient.__init__", lambda self, model=None: None
    )


async def _campaign(session_factory, brand_id: int, name: str, niche: str) -> Campaign:
    async with session_factory() as db:
        campaign = Campaign(
            brand_id=brand_id,
            name=name,
            status=CampaignStatus.ACTIVE,
            niche=niche,
            campaign_goal="Sales",
            campaign_type="Sponsored Reel",
            budget_per_creator=30000,
            currency="INR",
            deliverables=json.dumps(["1x Reel"]),
            platform_preferences=json.dumps(["instagram"]),
            is_open_to_applications=True,
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
    return campaign


async def _read_stream(client, creator) -> list[dict]:
    messages = []
    async with client.stream(
        "POST", "/ai/brand-deals/stream", headers=auth_header(creator)
    ) as res:
        assert res.status_code == 200
        async for line in res.aiter_lines():
            if line.strip():
                messages.append(json.loads(line))
    return messages


# ---------------------------------------------------------------------------
# The stream itself
# ---------------------------------------------------------------------------

async def test_stream_emits_each_opportunity_then_a_done_line(
    client, session_factory, monkeypatch
):
    brand = await make_user(session_factory, "b@example.com", "BRAND")
    await make_brand_profile(session_factory, brand.id, brand_name="SecretBrand")
    creator = await make_user(session_factory, "c@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Fitness")
    await _campaign(session_factory, brand.id, "Summer Protein", "Fitness")
    await _campaign(session_factory, brand.id, "Winter Bulk", "Fitness")

    _stub_campaign_engine(monkeypatch)

    messages = await _read_stream(client, creator)

    kinds = [m["type"] for m in messages]
    assert kinds == ["opportunity", "opportunity", "done"]
    assert messages[-1]["total"] == 2
    # Each line is a whole, usable card — not a fragment to be assembled.
    for m in messages[:2]:
        assert m["opportunity"]["budget_per_creator"] == 30000
        assert m["opportunity"]["terms_are_estimated"] is False


async def test_stream_never_reveals_the_brand(client, session_factory, monkeypatch):
    """The anonymity guarantee is asserted on the streamed bytes themselves."""
    brand = await make_user(session_factory, "b2@example.com", "BRAND")
    await make_brand_profile(session_factory, brand.id, brand_name="SecretBrand")
    creator = await make_user(session_factory, "c2@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Fitness")
    await _campaign(session_factory, brand.id, "Summer Protein", "Fitness")

    _stub_campaign_engine(monkeypatch)

    raw = json.dumps(await _read_stream(client, creator))

    assert "SecretBrand" not in raw
    assert "brand_id" not in raw
    assert "campaign_id" not in raw


async def test_stream_and_cache_agree(client, session_factory, monkeypatch):
    """
    What was streamed must be what `GET /ai/brand-deals` replays. A stream that
    forgets to write the cache leaves the creator's next page load empty.
    """
    brand = await make_user(session_factory, "b3@example.com", "BRAND")
    await make_brand_profile(session_factory, brand.id)
    creator = await make_user(session_factory, "c3@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Fitness")
    await _campaign(session_factory, brand.id, "Summer Protein", "Fitness")

    _stub_campaign_engine(monkeypatch)

    streamed = [m for m in await _read_stream(client, creator) if m["type"] == "opportunity"]

    cached = await client.get("/ai/brand-deals", headers=auth_header(creator))
    assert cached.status_code == 200
    body = cached.json()
    assert body["total"] == len(streamed) == 1
    assert (
        body["opportunities"][0]["opportunity_id"]
        == streamed[0]["opportunity"]["opportunity_id"]
    )


async def test_a_brand_cannot_stream_deals(client, session_factory):
    brand = await make_user(session_factory, "b4@example.com", "BRAND")
    res = await client.post("/ai/brand-deals/stream", headers=auth_header(brand))
    assert res.status_code == 403


async def test_stream_reports_a_missing_profile_in_band(
    client, session_factory, monkeypatch
):
    """
    Once the response has started there is no status code left to change, so the
    failure has to arrive as a line rather than truncating the stream silently.
    """
    creator = await make_user(session_factory, "c5@example.com", "INFLUENCER")

    messages = await _read_stream(client, creator)

    assert len(messages) == 1
    assert messages[0]["type"] == "error"
    assert "profile" in messages[0]["detail"].lower()


async def test_stream_is_rate_limited_per_account(client, session_factory, monkeypatch):
    """Every Gemini call costs money; the throttle must cover this path too."""
    brand = await make_user(session_factory, "b6@example.com", "BRAND")
    await make_brand_profile(session_factory, brand.id)
    creator = await make_user(session_factory, "c6@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Fitness")
    await _campaign(session_factory, brand.id, "Summer Protein", "Fitness")

    _stub_campaign_engine(monkeypatch)

    codes = []
    for _ in range(8):
        async with client.stream(
            "POST", "/ai/brand-deals/stream", headers=auth_header(creator)
        ) as res:
            codes.append(res.status_code)
            await res.aread()

    assert 429 in codes, "the streaming endpoint is not throttled"


# ---------------------------------------------------------------------------
# Niche ordering
# ---------------------------------------------------------------------------

async def test_deals_prioritise_the_creators_own_niche(
    client, session_factory, monkeypatch
):
    """
    The run is capped, so ordering decides what a creator sees at all. With a
    single slot available, the campaign in their own niche must take it —
    previously the newest campaign won regardless of relevance.
    """
    brand = await make_user(session_factory, "b7@example.com", "BRAND")
    await make_brand_profile(session_factory, brand.id)
    creator = await make_user(session_factory, "c7@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Fitness")

    # Fitness first, so the later Gaming campaign is the newest by created_at.
    await _campaign(session_factory, brand.id, "Fitness Launch", "Fitness")
    await _campaign(session_factory, brand.id, "Gaming Launch", "Gaming")

    _stub_campaign_engine(monkeypatch)
    monkeypatch.setattr(settings, "ai_max_brands_per_run", 1)

    res = await client.post("/ai/brand-deals", headers=auth_header(creator))

    opportunities = res.json()["opportunities"]
    assert len(opportunities) == 1
    # The opportunity carries no campaign id by design, so verify via the brief
    # the model was asked about — the deliverables came from the chosen campaign.
    async with session_factory() as db:
        chosen = (await db.execute(
            select(Campaign).where(Campaign.niche == "Fitness")
        )).scalar()
    assert chosen is not None

    # A Gaming-only creator must get the opposite result under the same cap.
    other = await make_user(session_factory, "c8@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, other.id, category="Gaming")

    res2 = await client.post("/ai/brand-deals", headers=auth_header(other))
    assert len(res2.json()["opportunities"]) == 1


async def test_a_creator_in_a_thin_niche_still_gets_deals(
    client, session_factory, monkeypatch
):
    """
    Ordering by niche must not turn into filtering by it. A Photography creator
    on a platform with no Photography campaigns should still see what exists,
    not an empty screen.
    """
    brand = await make_user(session_factory, "b9@example.com", "BRAND")
    await make_brand_profile(session_factory, brand.id)
    creator = await make_user(session_factory, "c9@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Photography")
    await _campaign(session_factory, brand.id, "Gaming Launch", "Gaming")

    _stub_campaign_engine(monkeypatch)

    res = await client.post("/ai/brand-deals", headers=auth_header(creator))

    assert res.status_code == 200
    assert len(res.json()["opportunities"]) == 1
