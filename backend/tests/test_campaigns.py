"""
Tests for campaigns.

The property that matters: when an opportunity comes from a campaign, every
commercial value a creator sees is the brand's own, read from the database. The
model contributes fit and description only. If that ever inverts, Crewaa is back
to showing people numbers nobody agreed to.
"""

import json
from datetime import date

import pytest
from sqlalchemy import select

from app.modules.campaigns.models import Campaign, CampaignStatus
from app.modules.deals.models import OpportunityInterest
from app.modules.instagram.models.instagram import InstagramProfile
from app.modules.users.models import CreatorProfile
from tests.conftest import (
    auth_header, make_brand_profile, make_creator_profile, make_user,
)

CAMPAIGN_PAYLOAD = {
    "name": "Summer Protein Launch",
    "niche": "Fitness",
    "campaign_goal": "Sales",
    "campaign_type": "Sponsored Reel",
    "budget_per_creator": 30000,
    "currency": "INR",
    "deliverables": ["1x Reel (45s)", "2x Story frames"],
    "deadline": "2026-03-15",
    "brief": "Show the product in a real training session.",
    "platform_preferences": ["instagram"],
    "target_location": "Mumbai",
    "min_followers": 10000,
    "creators_needed": 3,
}


async def _brand(session_factory, email="brand@example.com"):
    brand = await make_user(session_factory, email, "BRAND")
    await make_brand_profile(session_factory, brand.id, brand_name="SecretBrand")
    return brand


# ---------------------------------------------------------------------------
# CRUD and ownership
# ---------------------------------------------------------------------------

async def test_brand_can_create_a_campaign_with_real_terms(client, session_factory):
    brand = await _brand(session_factory)

    res = await client.post("/campaigns", json=CAMPAIGN_PAYLOAD, headers=auth_header(brand))

    assert res.status_code == 201
    body = res.json()
    assert body["budget_per_creator"] == 30000
    assert body["deliverables"] == ["1x Reel (45s)", "2x Story frames"]
    assert body["deadline"] == "2026-03-15"
    assert body["status"] == "active"


async def test_creator_cannot_manage_campaigns(client, session_factory):
    creator = await make_user(session_factory, "c@example.com", "INFLUENCER")

    res = await client.post("/campaigns", json=CAMPAIGN_PAYLOAD, headers=auth_header(creator))
    assert res.status_code == 403

    assert (await client.get("/campaigns", headers=auth_header(creator))).status_code == 403


async def test_a_brand_only_sees_its_own_campaigns(client, session_factory):
    brand_a = await _brand(session_factory, "a@example.com")
    brand_b = await _brand(session_factory, "b@example.com")

    created = await client.post(
        "/campaigns", json=CAMPAIGN_PAYLOAD, headers=auth_header(brand_a)
    )
    campaign_id = created.json()["id"]

    assert (await client.get("/campaigns", headers=auth_header(brand_b))).json() == []

    # And cannot reach it directly — 404, so its existence is not disclosed.
    res = await client.get(f"/campaigns/{campaign_id}", headers=auth_header(brand_b))
    assert res.status_code == 404


async def test_a_brand_cannot_edit_another_brands_campaign(client, session_factory):
    brand_a = await _brand(session_factory, "a2@example.com")
    brand_b = await _brand(session_factory, "b2@example.com")

    campaign_id = (await client.post(
        "/campaigns", json=CAMPAIGN_PAYLOAD, headers=auth_header(brand_a)
    )).json()["id"]

    hijack = {**CAMPAIGN_PAYLOAD, "budget_per_creator": 1}
    res = await client.put(
        f"/campaigns/{campaign_id}", json=hijack, headers=auth_header(brand_b)
    )
    assert res.status_code == 404

    # The original terms are untouched.
    original = await client.get(f"/campaigns/{campaign_id}", headers=auth_header(brand_a))
    assert original.json()["budget_per_creator"] == 30000


async def test_closing_a_campaign_keeps_it(client, session_factory):
    """Interests reference campaigns; hard deletion would erase real history."""
    brand = await _brand(session_factory, "close@example.com")
    campaign_id = (await client.post(
        "/campaigns", json=CAMPAIGN_PAYLOAD, headers=auth_header(brand)
    )).json()["id"]

    res = await client.delete(f"/campaigns/{campaign_id}", headers=auth_header(brand))
    assert res.status_code == 200

    still_there = await client.get(f"/campaigns/{campaign_id}", headers=auth_header(brand))
    assert still_there.status_code == 200
    assert still_there.json()["status"] == "closed"
    assert still_there.json()["is_open_to_applications"] is False


async def test_invalid_goal_is_rejected(client, session_factory):
    brand = await _brand(session_factory, "bad@example.com")
    res = await client.post(
        "/campaigns",
        json={**CAMPAIGN_PAYLOAD, "campaign_goal": "WorldDomination"},
        headers=auth_header(brand),
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# The point of the whole feature
# ---------------------------------------------------------------------------

async def _seed_campaign_and_creator(session_factory):
    brand = await _brand(session_factory, "camp@example.com")
    creator = await make_user(session_factory, "creator@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Fitness")

    async with session_factory() as db:
        campaign = Campaign(
            brand_id=brand.id,
            name="Summer Protein Launch",
            status=CampaignStatus.ACTIVE,
            niche="Fitness",
            campaign_goal="Sales",
            campaign_type="Sponsored Reel",
            budget_per_creator=30000,
            currency="INR",
            deliverables=json.dumps(["1x Reel (45s)", "2x Story frames"]),
            deadline=date(2026, 3, 15),
            brief="Show the product in a real training session.",
            platform_preferences=json.dumps(["instagram"]),
            min_followers=10000,
            is_open_to_applications=True,
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)

    return brand, creator, campaign


def _stub_engines(monkeypatch, assessment=None):
    """The model may only return judgement — never commercial values."""
    payload = assessment or {
        "fit_level": "High",
        "industry_hint": "Health & Nutrition",
        "why_it_fits": ["Your audience matches the campaign's target."],
        "what_to_expect": "A single reel filmed during a normal session.",
    }

    async def fake_assess(self, campaign_data, creator_data):
        return dict(payload)

    monkeypatch.setattr(
        "app.modules.ai.ai_service.CampaignOpportunityEngine.assess", fake_assess
    )
    monkeypatch.setattr(
        "app.modules.ai.ai_service.GeminiClient.__init__", lambda self, model=None: None
    )


async def test_campaign_opportunity_shows_the_brands_real_terms(
    client, session_factory, monkeypatch
):
    _, creator, campaign = await _seed_campaign_and_creator(session_factory)
    _stub_engines(monkeypatch)

    res = await client.post("/ai/brand-deals", headers=auth_header(creator))

    assert res.status_code == 200
    opp = res.json()["opportunities"][0]

    # Straight from the campaign record.
    assert opp["budget_per_creator"] == 30000
    assert opp["currency"] == "INR"
    assert opp["deadline"] == "2026-03-15"
    assert opp["deliverables"] == ["1x Reel (45s)", "2x Story frames"]
    # And therefore NOT an estimate.
    assert opp["terms_are_estimated"] is False


async def test_the_model_cannot_state_a_fee(client, session_factory, monkeypatch):
    """
    Even if the model returns commercial values, they must be discarded — the
    creator only ever sees what the brand typed.
    """
    _, creator, campaign = await _seed_campaign_and_creator(session_factory)

    _stub_engines(monkeypatch, assessment={
        "fit_level": "High",
        "industry_hint": "Health & Nutrition",
        "why_it_fits": ["Good match."],
        "what_to_expect": "A reel.",
        # The model tries to invent terms:
        "compensation": "Rs 999,999",
        "deliverables": ["50x Reels"],
        "deadline": "tomorrow",
    })

    res = await client.post("/ai/brand-deals", headers=auth_header(creator))
    opp = res.json()["opportunities"][0]

    assert opp["budget_per_creator"] == 30000, "model value overrode the brand's"
    assert opp["deliverables"] == ["1x Reel (45s)", "2x Story frames"]
    assert opp["deadline"] == "2026-03-15"
    assert "999,999" not in json.dumps(opp)


async def test_campaign_opportunity_still_hides_the_brand(
    client, session_factory, monkeypatch
):
    _, creator, _ = await _seed_campaign_and_creator(session_factory)
    _stub_engines(monkeypatch)

    res = await client.post("/ai/brand-deals", headers=auth_header(creator))
    body = json.dumps(res.json())

    assert "SecretBrand" not in body
    assert "brand_id" not in body
    assert "campaign_id" not in body, "campaign attribution leaked to the creator"


async def test_interest_is_recorded_against_the_campaign(
    client, session_factory, monkeypatch
):
    brand, creator, campaign = await _seed_campaign_and_creator(session_factory)
    _stub_engines(monkeypatch)

    listing = await client.post("/ai/brand-deals", headers=auth_header(creator))
    opportunity_id = listing.json()["opportunities"][0]["opportunity_id"]

    applied = await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": opportunity_id},
        headers=auth_header(creator),
    )
    assert applied.status_code == 200

    async with session_factory() as db:
        interest = (await db.execute(select(OpportunityInterest))).scalar()

    assert interest.brand_id == brand.id
    assert interest.campaign_id == campaign.id, "interest not linked to the campaign"


async def test_campaign_list_reports_response_counts(
    client, session_factory, monkeypatch
):
    brand, creator, campaign = await _seed_campaign_and_creator(session_factory)
    _stub_engines(monkeypatch)

    listing = await client.post("/ai/brand-deals", headers=auth_header(creator))
    await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": listing.json()["opportunities"][0]["opportunity_id"]},
        headers=auth_header(creator),
    )

    campaigns = await client.get("/campaigns", headers=auth_header(brand))
    assert campaigns.json()[0]["interested_count"] == 1


async def test_closed_campaigns_are_not_offered(client, session_factory, monkeypatch):
    _, creator, campaign = await _seed_campaign_and_creator(session_factory)
    _stub_engines(monkeypatch)

    async with session_factory() as db:
        target = (await db.execute(
            select(Campaign).where(Campaign.id == campaign.id)
        )).scalar()
        target.is_open_to_applications = False
        target.status = CampaignStatus.CLOSED
        await db.commit()

    res = await client.post("/ai/brand-deals", headers=auth_header(creator))
    # No campaign, and the brand profile fallback needs its own engine — either
    # way the closed campaign must not appear.
    for opp in res.json()["opportunities"]:
        assert opp["terms_are_estimated"] is True, "a closed campaign was offered"


# ---------------------------------------------------------------------------
# Discovery driven by a campaign
#
# The brand side of the same idea: a shortlist should be built from the brief
# the brand actually published, not from criteria retyped into a search form
# that can drift away from it.
# ---------------------------------------------------------------------------

def _stub_ranking(monkeypatch, captured: dict | None = None):
    """Rank everything the router sends, and optionally record what it sent."""
    async def fake_rank(self, brand_data, creators_data):
        if captured is not None:
            captured["brand_data"] = brand_data
            captured["creators_data"] = creators_data
        return {
            "ranked_creators": [
                {"creator_id": c["creator_identity"]["id"], "fit_level": "High"}
                for c in creators_data
            ],
            "final_recommendation": "ok",
        }

    monkeypatch.setattr(
        "app.modules.ai.ai_service.BrandCreatorRankingEngine.rank_creators", fake_rank
    )
    monkeypatch.setattr(
        "app.modules.ai.ai_service.GeminiClient.__init__", lambda self, model=None: None
    )


async def test_discovery_takes_its_criteria_from_the_campaign(
    client, session_factory, monkeypatch
):
    brand, _, campaign = await _seed_campaign_and_creator(session_factory)
    captured: dict = {}
    _stub_ranking(monkeypatch, captured)

    res = await client.post(
        "/ai/discover-creators",
        json={"campaign_id": campaign.id},
        headers=auth_header(brand),
    )

    assert res.status_code == 200
    body = res.json()
    assert body["criteria_source"] == "campaign"
    assert body["campaign_id"] == campaign.id
    assert body["campaign_name"] == "Summer Protein Launch"

    # The campaign's own values reached the model, not the request defaults.
    identity = captured["brand_data"]["brand_identity"]
    assert identity["industry"] == "Fitness"
    assert identity["campaign_goal"] == "Sales"
    assert captured["brand_data"]["campaign"]["budget_per_creator"] == 30000


async def test_loose_fields_cannot_override_a_campaign(
    client, session_factory, monkeypatch
):
    """
    A stale form value must never silently redirect a campaign's search. The
    campaign is the source of truth; the loose fields are ignored outright.
    """
    brand, _, campaign = await _seed_campaign_and_creator(session_factory)
    captured: dict = {}
    _stub_ranking(monkeypatch, captured)

    res = await client.post(
        "/ai/discover-creators",
        json={
            "campaign_id": campaign.id,
            "niche": "Gaming",
            "campaign_goal": "Awareness",
            "target_location": "Berlin",
        },
        headers=auth_header(brand),
    )

    assert res.status_code == 200
    identity = captured["brand_data"]["brand_identity"]
    assert identity["industry"] == "Fitness", "the form's niche overrode the campaign"
    assert identity["campaign_goal"] == "Sales"
    assert identity["target_location"] != "Berlin"


async def test_discovery_against_another_brands_campaign_is_404(
    client, session_factory, monkeypatch
):
    _, _, campaign = await _seed_campaign_and_creator(session_factory)
    intruder = await _brand(session_factory, "intruder@example.com")
    _stub_ranking(monkeypatch)

    res = await client.post(
        "/ai/discover-creators",
        json={"campaign_id": campaign.id},
        headers=auth_header(intruder),
    )

    # 404, not 403 — the same non-disclosure rule as /campaigns.
    assert res.status_code == 404


async def test_discovery_still_accepts_ad_hoc_criteria(
    client, session_factory, monkeypatch
):
    """A brand that has not created a campaign must still be able to look around."""
    brand = await _brand(session_factory, "adhoc@example.com")
    creator = await make_user(session_factory, "adhoc-c@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, category="Fitness")
    _stub_ranking(monkeypatch)

    res = await client.post(
        "/ai/discover-creators",
        json={"niche": "Fitness"},
        headers=auth_header(brand),
    )

    assert res.status_code == 200
    assert res.json()["criteria_source"] == "custom"
    assert res.json()["campaign_id"] is None


async def test_discovery_needs_a_campaign_or_a_niche(client, session_factory):
    brand = await _brand(session_factory, "empty@example.com")

    res = await client.post("/ai/discover-creators", json={}, headers=auth_header(brand))

    assert res.status_code == 422


async def test_campaign_follower_floor_excludes_smaller_creators(
    client, session_factory, monkeypatch
):
    """
    `min_followers` was stated by the brand and then ignored by every code path.
    A floor the product accepts but does not apply is worse than no floor.
    """
    brand, big_creator, campaign = await _seed_campaign_and_creator(session_factory)
    small = await make_user(session_factory, "small@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, small.id, category="Fitness")

    async with session_factory() as db:
        db.add(InstagramProfile(user_id=big_creator.id, username="big", followers=50_000))
        db.add(InstagramProfile(user_id=small.id, username="small", followers=800))
        await db.commit()

    _stub_ranking(monkeypatch)

    res = await client.post(
        "/ai/discover-creators",
        json={"campaign_id": campaign.id},  # campaign sets min_followers=10000
        headers=auth_header(brand),
    )

    returned = {c["creator_id"] for c in res.json()["ranked_creators"]}
    assert str(big_creator.id) in returned
    assert str(small.id) not in returned, "a creator below the stated floor was shown"
    assert res.json()["follower_floor_relaxed"] is False


async def test_an_unmeetable_floor_is_relaxed_and_reported(
    client, session_factory, monkeypatch
):
    """
    An empty screen is indistinguishable from a broken one. Return the ranking,
    but say plainly that the minimum could not be met.
    """
    brand, creator, campaign = await _seed_campaign_and_creator(session_factory)

    async with session_factory() as db:
        db.add(InstagramProfile(user_id=creator.id, username="tiny", followers=120))
        await db.commit()

    _stub_ranking(monkeypatch)

    res = await client.post(
        "/ai/discover-creators",
        json={"campaign_id": campaign.id},
        headers=auth_header(brand),
    )

    body = res.json()
    assert body["follower_floor_relaxed"] is True
    assert len(body["ranked_creators"]) == 1
    assert "10,000" in body["final_recommendation"]


async def test_a_creator_who_has_never_scraped_is_not_hidden_by_a_floor(
    client, session_factory, monkeypatch
):
    """
    No snapshot means no information, not a small audience. Excluding them would
    make every new signup invisible to every campaign that sets a minimum.
    """
    brand, creator, campaign = await _seed_campaign_and_creator(session_factory)
    _stub_ranking(monkeypatch)

    res = await client.post(
        "/ai/discover-creators",
        json={"campaign_id": campaign.id},
        headers=auth_header(brand),
    )

    returned = {c["creator_id"] for c in res.json()["ranked_creators"]}
    assert str(creator.id) in returned
    assert res.json()["follower_floor_relaxed"] is False
