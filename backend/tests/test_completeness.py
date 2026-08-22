"""
Tests for computed profile completeness.

The `is_completed` column defaulted to True and was never set to False, so the
admin console showed a green tick for every user including ones with no name and
no linked account. A flag that cannot be wrong because it never varies is worse
than no flag: someone eventually trusts it.
"""

import pytest

from app.modules.users.completeness import brand_completeness, creator_completeness
from tests.conftest import (
    auth_header, make_brand_profile, make_creator_profile, make_user,
)


class _Creator:
    def __init__(self, **kw):
        self.full_name = kw.get("full_name", "Aarav Mehta")
        self.category = kw.get("category", "Fitness")
        self.instagram_username = kw.get("instagram_username", "aaravfits")
        self.youtube_username = kw.get("youtube_username")


class _Brand:
    def __init__(self, **kw):
        self.brand_name = kw.get("brand_name", "NutriFlex")
        self.industry = kw.get("industry", "Fitness")


def test_a_filled_creator_profile_is_complete():
    assert creator_completeness(_Creator()).complete is True


def test_a_missing_profile_is_not_complete():
    result = creator_completeness(None)
    assert result.complete is False
    assert result.missing == ["profile"]


@pytest.mark.parametrize("field,expected", [
    ("full_name", "name"),
    ("category", "niche"),
])
def test_each_required_creator_field_is_reported_by_name(field, expected):
    result = creator_completeness(_Creator(**{field: ""}))
    assert result.complete is False
    assert expected in result.missing


def test_either_platform_satisfies_the_handle_requirement():
    """One linked account is enough — requiring both would be wrong."""
    ig_only = _Creator(instagram_username="x", youtube_username=None)
    yt_only = _Creator(instagram_username=None, youtube_username="y")
    neither = _Creator(instagram_username=None, youtube_username=None)

    assert creator_completeness(ig_only).complete is True
    assert creator_completeness(yt_only).complete is True
    assert creator_completeness(neither).complete is False
    assert "Instagram or YouTube handle" in creator_completeness(neither).missing


def test_optional_fields_do_not_make_a_profile_incomplete():
    """
    Location and bio are useful but not required. A creator without them still
    ranks and still receives opportunities, so telling them they are incomplete
    would be a lie that costs a signup.
    """
    sparse = _Creator()
    sparse.location = None
    sparse.bio = None
    assert creator_completeness(sparse).complete is True


def test_whitespace_does_not_count_as_filled_in():
    assert creator_completeness(_Creator(full_name="   ")).complete is False


def test_brand_completeness_needs_a_name_and_an_industry():
    assert brand_completeness(_Brand()).complete is True
    assert brand_completeness(_Brand(industry="")).missing == ["industry"]
    assert brand_completeness(_Brand(brand_name="")).missing == ["brand name"]


# ---------------------------------------------------------------------------
# Through the API
# ---------------------------------------------------------------------------

async def test_admin_sees_a_truthful_flag_for_an_incomplete_creator(
    client, session_factory
):
    """The regression that motivated this: everyone showed as complete."""
    admin = await make_user(session_factory, "admin@example.com", "ADMIN")
    creator = await make_user(session_factory, "half@example.com", "INFLUENCER")
    await make_creator_profile(
        session_factory, creator.id,
        full_name="", instagram_username=None, youtube_username=None,
    )

    res = await client.get(f"/admin/users/{creator.id}", headers=auth_header(admin))

    body = res.json()
    assert body["creator_profile_completed"] is False, (
        "the admin console is still reporting the dead is_completed column"
    )
    assert "name" in body["creator_profile_missing"]
    assert "Instagram or YouTube handle" in body["creator_profile_missing"]


async def test_admin_sees_a_complete_creator_as_complete(client, session_factory):
    admin = await make_user(session_factory, "admin2@example.com", "ADMIN")
    creator = await make_user(session_factory, "full@example.com", "INFLUENCER")
    await make_creator_profile(session_factory, creator.id, full_name="Aarav")

    res = await client.get(f"/admin/users/{creator.id}", headers=auth_header(admin))

    assert res.json()["creator_profile_completed"] is True
    assert res.json()["creator_profile_missing"] == []


async def test_profile_status_and_admin_agree(client, session_factory):
    """
    Two definitions of "complete" drifting apart is exactly what putting the rule
    in one module is meant to prevent, so it is asserted rather than assumed.
    """
    admin = await make_user(session_factory, "admin3@example.com", "ADMIN")
    creator = await make_user(session_factory, "agree@example.com", "INFLUENCER")
    await make_creator_profile(
        session_factory, creator.id, full_name="Aarav", category="",
    )

    own = await client.get("/users/profile-status", headers=auth_header(creator))
    seen_by_admin = await client.get(
        f"/admin/users/{creator.id}", headers=auth_header(admin)
    )

    assert own.json()["is_complete"] == seen_by_admin.json()["creator_profile_completed"]
    assert own.json()["missing"] == seen_by_admin.json()["creator_profile_missing"]
