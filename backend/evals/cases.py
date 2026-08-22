"""
Golden cases for the prompt evals.

Every case here has an answer that is defensible without knowing anything about
Crewaa's implementation — a Fitness campaign should not rank a Food creator
first, a 3%-engagement account with 500k followers is not automatically a worse
fit than an 8% account with 20k, and an opportunity shown to a creator must
never name the brand behind it.

That constraint matters. An eval whose expectations were derived from watching
the current model's output would only ever confirm that the model still does
what it did last week, which is not the same as doing the right thing. So each
case carries a `rationale`: the reason a person would give for the expected
answer, written before any model was run.

Deliberately small. Ten cases that are each individually arguable beat a hundred
generated ones nobody has read, because a failing eval is only useful if you can
tell whether the model is wrong or the expectation is.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Creator fixtures — shaped exactly like `_build_creator_payloads` output, so
# the evals exercise the same payloads production sends.
# ---------------------------------------------------------------------------

def _creator(
    cid: str, name: str, niche: str, location: str,
    followers: int, engagement: float, bio: str = "",
    subscribers: int | None = None,
) -> dict:
    platforms = [{
        "platform": "instagram",
        "username": name.lower().replace(" ", ""),
        "verified": followers > 100_000,
        "bio": bio,
        "followers": followers,
        "following": 500,
        "engagement": {
            "avg_likes": int(followers * engagement / 100 * 0.9),
            "avg_comments": int(followers * engagement / 100 * 0.1),
            "engagement_rate": engagement,
        },
        "recent_posts": [
            {"type": "reel", "caption": bio[:80], "likes": int(followers * engagement / 100),
             "comments": 40}
        ],
    }]
    if subscribers:
        platforms.append({
            "platform": "youtube", "username": name.lower().replace(" ", ""),
            "title": name, "description": bio[:120], "subscribers": subscribers,
            "total_views": subscribers * 30, "total_videos": 120, "recent_videos": [],
        })

    return {
        "creator_identity": {
            "id": cid, "name": name, "primary_niche": niche,
            "location": location, "pricing": "Mid",
        },
        "platforms": platforms,
    }


AARAV = _creator("1", "Aarav Mehta", "Fitness", "Mumbai", 142_500, 4.9,
                 "Strength coach. Programmes for lifters.", subscribers=71_300)
DIYA = _creator("2", "Diya Kapoor", "Beauty", "Bengaluru", 89_300, 6.2,
                "Skincare, honest reviews, no filters.")
ROHAN = _creator("3", "Rohan Iyer", "Tech", "Pune", 512_000, 3.1,
                 "Gadgets and deep dives.", subscribers=256_000)
MEERA = _creator("4", "Meera Nair", "Food", "Kochi", 23_800, 8.4,
                 "Kerala home cooking, one pot at a time.")
KABIR = _creator("5", "Kabir Shah", "Fitness", "Mumbai", 9_400, 11.2,
                 "Calisthenics. Small account, loud community.")

ALL_CREATORS = [AARAV, DIYA, ROHAN, MEERA, KABIR]


def _brand(niche: str, goal: str = "Sales", location: str = "Mumbai", **extra) -> dict:
    data = {
        "brand_identity": {
            "brand_name": "NutriFlex",
            "industry": niche,
            "campaign_goal": goal,
            "budget_range": "Mid",
            "target_location": location,
            "target_languages": ["English"],
        },
        "platform_preferences": ["instagram"],
    }
    data.update(extra)
    return data


# ---------------------------------------------------------------------------
# Ranking cases
# ---------------------------------------------------------------------------

@dataclass
class RankingCase:
    id: str
    brand_data: dict
    creators: list[dict]
    #: Ids that would be a defensible #1. More than one where the trade-off is
    #: genuinely arguable — an eval that demands one answer to an ambiguous
    #: question measures conformity, not quality.
    acceptable_top: set[str]
    #: Ids that must never be rated "High". These are the hard failures.
    forbidden_high: set[str] = field(default_factory=set)
    rationale: str = ""


RANKING_CASES = [
    RankingCase(
        id="niche-match-beats-reach",
        brand_data=_brand("Fitness"),
        creators=ALL_CREATORS,
        acceptable_top={"1", "5"},
        forbidden_high={"3", "4"},
        rationale=(
            "A Fitness campaign. Aarav (Fitness, 142k) and Kabir (Fitness, 9k but "
            "11% engagement) are both defensible tops. Rohan has 3.5x Aarav's reach "
            "but sells gadgets, and Meera cooks — rating either 'High' for a protein "
            "brand is the failure this platform exists to avoid."
        ),
    ),
    RankingCase(
        id="wrong-niche-is-not-high-fit",
        brand_data=_brand("Beauty", goal="Awareness", location="Bengaluru"),
        creators=ALL_CREATORS,
        acceptable_top={"2"},
        forbidden_high={"1", "3", "5"},
        rationale=(
            "Only Diya is a Beauty creator, and she is in the target city. There is "
            "no honest argument for a strength coach or a gadget reviewer being a "
            "High fit for a skincare launch."
        ),
    ),
    RankingCase(
        id="thin-niche-still-returns-something",
        brand_data=_brand("Photography", goal="Awareness"),
        creators=ALL_CREATORS,
        acceptable_top={"1", "2", "3", "4", "5"},
        forbidden_high={"1", "2", "3", "4", "5"},
        rationale=(
            "No creator matches Photography. The model must still rank everyone "
            "(an empty screen is a worse product than a hedged one) but must not "
            "claim any of them is a High fit. This is the case that catches a model "
            "that flatters the brand rather than telling it the truth."
        ),
    ),
    RankingCase(
        id="location-is-a-tiebreaker-not-a-filter",
        brand_data=_brand("Fitness", location="Kochi"),
        creators=ALL_CREATORS,
        acceptable_top={"1", "5"},
        forbidden_high={"3"},
        rationale=(
            "Campaign targets Kochi, where only Meera (Food) lives. Location should "
            "not outrank niche: a Fitness brand in Kochi is still better served by a "
            "Mumbai fitness creator than by a local food creator."
        ),
    ),
    RankingCase(
        id="engagement-quality-is-considered",
        brand_data=_brand("Fitness", goal="Engagement"),
        creators=[AARAV, KABIR],
        acceptable_top={"5", "1"},
        forbidden_high=set(),
        rationale=(
            "Goal is Engagement, not reach. Kabir has 15x fewer followers but more "
            "than double the engagement rate, so he is a legitimate #1 here — but "
            "Aarav is not wrong either. Both accepted; what is measured is that the "
            "model gives a reason that mentions engagement."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Campaign opportunity cases (the creator-facing side)
# ---------------------------------------------------------------------------

@dataclass
class OpportunityCase:
    id: str
    campaign_data: dict
    creator_data: dict
    expected_fit: set[str]
    #: Strings that must not appear anywhere in the output. Brand identity is a
    #: product promise, not a preference.
    forbidden_substrings: list[str] = field(default_factory=list)
    rationale: str = ""


def _campaign(niche: str, brand_name: str = "NutriFlex", **extra) -> dict:
    data = {
        "campaign": {
            "niche": niche,
            "goal": "Sales",
            "type": "Sponsored Reel",
            "budget_per_creator": 30000,
            "currency": "INR",
            "deliverables": ["1x Reel (45s)", "2x Story frames"],
            "deadline": "2026-03-15",
            "brief": "Show the product in a real training session.",
            "target_location": "Mumbai",
            "min_followers": 10000,
            "brand_name": brand_name,
        },
        "platform_preferences": ["instagram"],
    }
    data["campaign"].update(extra)
    return data


OPPORTUNITY_CASES = [
    OpportunityCase(
        id="strong-match-reads-as-strong",
        campaign_data=_campaign("Fitness"),
        creator_data=AARAV,
        expected_fit={"High", "Medium"},
        forbidden_substrings=["NutriFlex"],
        rationale=(
            "A Mumbai strength coach with 142k followers, offered a Mumbai protein "
            "campaign. If this does not read as at least a Medium fit, the matching "
            "is not working."
        ),
    ),
    OpportunityCase(
        id="mismatch-is-not-oversold",
        campaign_data=_campaign("Fitness"),
        creator_data=MEERA,
        expected_fit={"Low", "Medium"},
        forbidden_substrings=["NutriFlex"],
        rationale=(
            "A Kerala food creator offered a protein campaign. Calling this High "
            "wastes both sides' time and teaches creators to distrust the fit label."
        ),
    ),
    OpportunityCase(
        id="brand-identity-never-leaks",
        campaign_data=_campaign("Beauty", brand_name="Lumière Skincare"),
        creator_data=DIYA,
        expected_fit={"High", "Medium"},
        forbidden_substrings=["Lumière", "Lumiere", "Skincare Lumière"],
        rationale=(
            "Anonymity is the product promise on the creator side. Scrubbing "
            "enforces it in code; this checks the prompt is not fighting the "
            "scrubber by trying to name the brand in the first place."
        ),
    ),
]
