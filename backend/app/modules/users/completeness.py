"""
What "a complete profile" means, defined once.

Both profile tables carry an `is_completed` column that defaults to `True` and
is never set to `False`. The admin console displayed it, so it looked like
information while always saying the same thing — a field that cannot be wrong
because it never varies is worse than no field, since someone will eventually
trust it.

The fix is to compute it from the fields the product actually needs, and to do
that in one place so the admin console and the studio gating cannot drift into
two different definitions of "complete".

Required means *the product cannot do its job without it*, not *the form has a
box for it*. Location and bio are genuinely useful and deliberately not
required: a creator missing them still ranks, still gets opportunities, and
should not be told they are incomplete.
"""

from dataclasses import dataclass, field


@dataclass
class Completeness:
    complete: bool
    #: Human-readable names of what is missing, for the admin console and any
    #: "finish your profile" prompt. Empty when complete.
    missing: list[str] = field(default_factory=list)


def creator_completeness(profile) -> Completeness:
    """
    A creator profile is usable when a brand can see who they are, the matching
    engine knows their niche, and there is at least one account to analyse.
    """
    if profile is None:
        return Completeness(False, ["profile"])

    missing = []
    if not (profile.full_name or "").strip():
        # Without this a brand's shortlist shows "Creator" with no name.
        missing.append("name")
    if not (profile.category or "").strip():
        # Discovery and brand-deals both order by niche; blank means invisible.
        missing.append("niche")
    if not (profile.instagram_username or profile.youtube_username):
        # Nothing to scrape, so no audience numbers and no analytics.
        missing.append("Instagram or YouTube handle")

    return Completeness(not missing, missing)


def brand_completeness(profile) -> Completeness:
    """
    A brand profile is usable when it has a name to trade under and an industry
    to match creators against.

    Budget and campaign goal used to matter here; they moved to the campaign
    entity, where they are stated per campaign rather than once per brand.
    """
    if profile is None:
        return Completeness(False, ["profile"])

    missing = []
    if not (profile.brand_name or "").strip():
        missing.append("brand name")
    if not (profile.industry or "").strip():
        missing.append("industry")

    return Completeness(not missing, missing)
