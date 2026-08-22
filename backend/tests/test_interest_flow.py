"""
Tests for the expression-of-interest flow.

The critical property: a creator can act on an opportunity without ever learning
which brand it came from, while the brand learns who raised their hand. If that
asymmetry ever inverts, the Brand Deals feature breaks its core promise.
"""

import json

import pytest
from sqlalchemy import select

from app.modules.deals.models import InterestStatus, OpportunityInterest
from app.modules.users.models import CreatorProfile
from tests.conftest import (
    auth_header, make_brand_profile, make_creator_profile, make_user,
)

OPPORTUNITY_ID = "11111111-2222-3333-4444-555555555555"


def _cached_deal(brand_id: int, opportunity_id: str = OPPORTUNITY_ID) -> str:
    """A cached deal in the current, brand-attributed format."""
    return json.dumps([{
        "brand_id": brand_id,
        "opportunity": {
            "opportunity_id": opportunity_id,
            "fit_level": "High",
            "industry_hint": "Health & Nutrition",
            "campaign_type": "Sponsored Post",
            "campaign_requirements": "One reel",
            "compensation": "Rs 25,000 - 40,000",
            "timeline": "3 weeks",
            "deliverables": ["1x Reel"],
            "status": "open",
            "budget_range": "Mid",
            "terms_are_estimated": True,
        },
    }])


async def _seed(session_factory, cached: str | None = None):
    brand = await make_user(session_factory, "brand@example.com", "BRAND")
    await make_brand_profile(session_factory, brand.id, brand_name="SecretBrand")
    creator = await make_user(session_factory, "creator@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, full_name="Aarav Mehta")

    if cached is None:
        cached = _cached_deal(brand.id)

    async with session_factory() as db:
        profile = (await db.execute(
            select(CreatorProfile).where(CreatorProfile.user_id == creator.id)
        )).scalar()
        profile.cached_brand_deals = cached
        await db.commit()

    return brand, creator


# ---------------------------------------------------------------------------
# The anonymity boundary
# ---------------------------------------------------------------------------

async def test_brand_identity_never_reaches_the_creator(client, session_factory):
    brand, creator = await _seed(session_factory)

    res = await client.get("/ai/brand-deals", headers=auth_header(creator))

    assert res.status_code == 200
    body = res.json()

    # No brand-identifying key survives anywhere in the payload. Checked
    # structurally rather than by substring: the brand's numeric id would
    # otherwise "appear" inside unrelated values such as a uuid.
    def keys_anywhere(node) -> set[str]:
        if isinstance(node, dict):
            found = set(node)
            for value in node.values():
                found |= keys_anywhere(value)
            return found
        if isinstance(node, list):
            found: set[str] = set()
            for item in node:
                found |= keys_anywhere(item)
            return found
        return set()

    leaked = keys_anywhere(body) & {"brand_id", "brand_name", "website", "brand"}
    assert not leaked, f"brand attribution leaked to the creator: {leaked}"
    assert "SecretBrand" not in json.dumps(body)


async def test_creator_can_express_interest_without_knowing_the_brand(
    client, session_factory
):
    brand, creator = await _seed(session_factory)

    res = await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID, "message": "Would love to work on this"},
        headers=auth_header(creator),
    )

    assert res.status_code == 200
    assert res.json()["status"] == "interested"

    async with session_factory() as db:
        interest = (await db.execute(select(OpportunityInterest))).scalar()

    # The creator never sent a brand id; the server resolved it.
    assert interest.brand_id == brand.id
    assert interest.creator_id == creator.id
    assert interest.message == "Would love to work on this"


async def test_creator_cannot_express_interest_in_an_unoffered_opportunity(
    client, session_factory
):
    """Guards against a creator guessing or replaying someone else's id."""
    _, creator = await _seed(session_factory)

    res = await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": "99999999-0000-0000-0000-000000000000"},
        headers=auth_header(creator),
    )

    assert res.status_code == 404


async def test_expressing_interest_twice_updates_rather_than_duplicates(
    client, session_factory
):
    _, creator = await _seed(session_factory)

    await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID, "message": "first"},
        headers=auth_header(creator),
    )
    res = await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID, "message": "second"},
        headers=auth_header(creator),
    )

    assert res.status_code == 200
    async with session_factory() as db:
        rows = (await db.execute(select(OpportunityInterest))).scalars().all()

    assert len(rows) == 1
    assert rows[0].message == "second"


async def test_deals_show_which_ones_the_creator_already_applied_to(
    client, session_factory
):
    _, creator = await _seed(session_factory)

    before = await client.get("/ai/brand-deals", headers=auth_header(creator))
    assert before.json()["opportunities"][0]["interested"] is False

    await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID},
        headers=auth_header(creator),
    )

    after = await client.get("/ai/brand-deals", headers=auth_header(creator))
    assert after.json()["opportunities"][0]["interested"] is True


async def test_creator_can_withdraw(client, session_factory):
    _, creator = await _seed(session_factory)

    await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID},
        headers=auth_header(creator),
    )
    res = await client.delete(
        f"/ai/opportunities/interest/{OPPORTUNITY_ID}", headers=auth_header(creator)
    )

    assert res.status_code == 200
    async with session_factory() as db:
        interest = (await db.execute(select(OpportunityInterest))).scalar()
    assert interest.status == InterestStatus.WITHDRAWN


# ---------------------------------------------------------------------------
# The brand's side
# ---------------------------------------------------------------------------

async def test_brand_sees_interested_creators_with_contact_details(
    client, session_factory
):
    brand, creator = await _seed(session_factory)

    await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID, "message": "Big fan"},
        headers=auth_header(creator),
    )

    res = await client.get("/ai/interested-creators", headers=auth_header(brand))

    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    entry = body["creators"][0]
    assert entry["creator_name"] == "Aarav Mehta"
    # Disclosed because the creator opted in.
    assert entry["email"] == "creator@example.com"
    assert entry["message"] == "Big fan"
    assert entry["campaign_type"] == "Sponsored Post"


async def test_a_brand_only_sees_interest_in_its_own_opportunities(
    client, session_factory
):
    brand, creator = await _seed(session_factory)
    other_brand = await make_user(session_factory, "other@example.com", "BRAND")
    await make_brand_profile(session_factory, other_brand.id, brand_name="Other")

    await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID},
        headers=auth_header(creator),
    )

    res = await client.get("/ai/interested-creators", headers=auth_header(other_brand))
    assert res.json()["total"] == 0


async def test_withdrawn_interest_disappears_from_the_brand_list(
    client, session_factory
):
    brand, creator = await _seed(session_factory)

    await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID},
        headers=auth_header(creator),
    )
    await client.delete(
        f"/ai/opportunities/interest/{OPPORTUNITY_ID}", headers=auth_header(creator)
    )

    res = await client.get("/ai/interested-creators", headers=auth_header(brand))
    assert res.json()["total"] == 0


async def test_creator_cannot_read_the_interested_creators_list(client, session_factory):
    _, creator = await _seed(session_factory)
    res = await client.get("/ai/interested-creators", headers=auth_header(creator))
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Honest terms
# ---------------------------------------------------------------------------

async def test_opportunities_carry_the_verified_budget_and_the_estimate_flag(
    client, session_factory
):
    """
    Compensation is model-generated and must be labelled as such; budget_range
    is what the brand actually set.
    """
    _, creator = await _seed(session_factory)

    res = await client.get("/ai/brand-deals", headers=auth_header(creator))
    opp = res.json()["opportunities"][0]

    assert opp["budget_range"] == "Mid"
    assert opp["terms_are_estimated"] is True


async def test_legacy_cache_without_attribution_is_readable_but_not_applicable(
    client, session_factory
):
    """
    Caches written before brand attribution existed must not break the page —
    they just cannot be applied to until refreshed.
    """
    legacy = json.dumps([{
        "opportunity_id": OPPORTUNITY_ID,
        "fit_level": "High",
        "status": "open",
    }])
    _, creator = await _seed(session_factory, cached=legacy)

    listing = await client.get("/ai/brand-deals", headers=auth_header(creator))
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    apply = await client.post(
        "/ai/opportunities/interest",
        json={"opportunity_id": OPPORTUNITY_ID},
        headers=auth_header(creator),
    )
    assert apply.status_code == 409
    assert "refresh" in apply.json()["detail"].lower()
