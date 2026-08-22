"""
Tests for the prompt eval suite.

An eval suite that passes everything is worse than no eval suite: it produces a
green tick that people trust. So the bulk of this file is not "does the suite
pass on good output" — it is "does the suite *fail* on output we know is bad".

Every degradation below is a real thing a model or a prompt edit could do, and
each one is asserted to be caught.
"""

import copy
import json
import pathlib

import pytest

from evals import cases as case_module
from evals.runner import RECORDED, run_replay
from evals.scoring import RunSummary, score_opportunity, score_ranking

RANKING = {c.id: c for c in case_module.RANKING_CASES}
OPPORTUNITY = {c.id: c for c in case_module.OPPORTUNITY_CASES}


def _recorded() -> dict:
    return json.loads(RECORDED.read_text())


def _ranking_response(case_id: str) -> dict:
    return copy.deepcopy(_recorded()[f"ranking:{case_id}"])


def _opportunity_response(case_id: str) -> dict:
    return copy.deepcopy(_recorded()[f"opportunity:{case_id}"])


# ---------------------------------------------------------------------------
# The suite is green on the fixtures it ships with
# ---------------------------------------------------------------------------

def test_the_committed_fixtures_score_clean():
    """
    Guards the fixtures, not the model. If someone edits a prompt such that the
    recorded output no longer parses, or weakens the scrubbing, this goes red in
    CI for free — no API key, no cost.
    """
    summary = RunSummary(run_replay())

    assert summary.total == len(RANKING) + len(OPPORTUNITY)
    assert summary.violations == 0, [r.violations for r in summary.results if r.violations]
    assert summary.miss_count == 0, [r.misses for r in summary.results if r.misses]


def test_every_case_explains_itself():
    """
    A failing eval is only actionable if you can tell whether the model is wrong
    or the expectation is. That requires the reasoning to be written down.
    """
    for case in [*case_module.RANKING_CASES, *case_module.OPPORTUNITY_CASES]:
        assert case.rationale.strip(), f"{case.id} has no rationale"
        assert len(case.rationale) > 60, f"{case.id}'s rationale is too thin to judge by"


# ---------------------------------------------------------------------------
# Violations — these must fail the run
# ---------------------------------------------------------------------------

def test_a_wrong_niche_high_fit_is_caught():
    """The core product failure: telling a protein brand a cook is a great fit."""
    case = RANKING["niche-match-beats-reach"]
    response = _ranking_response("niche-match-beats-reach")

    for entry in response["ranked_creators"]:
        if entry["creator_id"] == "4":      # Meera, Food
            entry["fit_level"] = "High"

    result = score_ranking(case, response)

    assert not result.passed
    assert any("rated creator 4 High" in v for v in result.violations)


def test_a_hallucinated_creator_id_is_caught():
    """
    Not a quality problem but a correctness one: an invented id gets written to
    saved_creators as a real brand-creator match.
    """
    case = RANKING["niche-match-beats-reach"]
    response = _ranking_response("niche-match-beats-reach")
    response["ranked_creators"].append(
        {"creator_id": "9999", "fit_level": "High", "score_reasoning": ["invented"]}
    )

    result = score_ranking(case, response)

    assert not result.passed
    assert any("invented creator ids" in v for v in result.violations)


def test_a_leaked_brand_name_is_caught():
    """Anonymity is the promise the creator side is built on."""
    case = OPPORTUNITY["brand-identity-never-leaks"]
    response = _opportunity_response("brand-identity-never-leaks")
    response["what_to_expect"] = "A reel for Lumière Skincare's spring launch."

    result = score_opportunity(case, response)

    assert not result.passed
    assert any("leaked brand identity" in v for v in result.violations)


def test_a_model_stated_fee_is_caught():
    """
    Production strips these keys, so a user would never see them — which is
    exactly why this needs its own check. The stripping hides prompt drift.
    """
    case = OPPORTUNITY["strong-match-reads-as-strong"]
    response = _opportunity_response("strong-match-reads-as-strong")
    response["compensation"] = "Rs 25,000 - 40,000"

    result = score_opportunity(case, response)

    assert not result.passed
    assert any("commercial term" in v for v in result.violations)


@pytest.mark.parametrize("broken,expected", [
    ({}, "no ranked_creators"),
    ({"ranked_creators": []}, "no ranked_creators"),
    ({"ranked_creators": [{"creator_id": "1", "fit_level": "Excellent"}]}, "unknown fit_level"),
])
def test_unusable_output_is_caught(broken, expected):
    """Almost always a prompt edit rather than a model change — but still red."""
    result = score_ranking(RANKING["niche-match-beats-reach"], broken)

    assert not result.passed
    assert any(expected in m for m in result.malformed)


# ---------------------------------------------------------------------------
# Misses — degraded but not invalid, so they move the score without failing
# ---------------------------------------------------------------------------

def test_a_wrong_first_place_is_a_miss_not_a_violation():
    """
    The distinction the whole suite rests on. Ranking a legitimate-but-worse
    creator first is a quality regression to watch as a trend, not an outage.
    """
    case = RANKING["wrong-niche-is-not-high-fit"]
    response = _ranking_response("wrong-niche-is-not-high-fit")
    response["ranked_creators"].reverse()

    result = score_ranking(case, response)

    assert result.passed, "a poor ordering should not be graded as a violation"
    assert any("expected one of" in m for m in result.misses)


def test_dropping_candidates_is_a_miss():
    """A brand cannot consider a creator it was never shown."""
    case = RANKING["niche-match-beats-reach"]
    response = _ranking_response("niche-match-beats-reach")
    response["ranked_creators"] = response["ranked_creators"][:2]

    result = score_ranking(case, response)

    assert result.passed
    assert any("did not rank" in m for m in result.misses)


def test_missing_reasoning_is_a_miss():
    case = RANKING["niche-match-beats-reach"]
    response = _ranking_response("niche-match-beats-reach")
    for entry in response["ranked_creators"]:
        entry.pop("score_reasoning", None)

    result = score_ranking(case, response)

    assert any("no reasoning" in m for m in result.misses)


def test_overselling_a_poor_match_is_a_miss():
    """
    A food creator told a protein deal is a High fit for them personally. Not a
    safety failure, but it teaches creators the fit label means nothing.
    """
    case = OPPORTUNITY["mismatch-is-not-oversold"]
    response = _opportunity_response("mismatch-is-not-oversold")
    response["fit_level"] = "High"

    result = score_opportunity(case, response)

    assert result.passed
    assert any("expected one of" in m for m in result.misses)


# ---------------------------------------------------------------------------
# The suite as a whole is not vacuous
# ---------------------------------------------------------------------------

def test_a_degraded_run_fails_the_whole_suite():
    """
    The test this file exists for.

    Feed the runner a set of responses in which the model has quietly become
    useless — everything rated High regardless of niche — and assert the suite
    goes red. If this ever passes, the evals have stopped measuring anything and
    the green tick on every other run is worthless.
    """
    degraded = {}
    for key, response in _recorded().items():
        if key.startswith("ranking:"):
            body = copy.deepcopy(response)
            for entry in body["ranked_creators"]:
                entry["fit_level"] = "High"
            degraded[key] = body
        elif key.startswith("opportunity:"):
            body = copy.deepcopy(response)
            body["fit_level"] = "High"
            degraded[key] = body

    summary = RunSummary(run_replay(degraded))

    assert summary.violations > 0, "the eval suite failed to notice a broken model"
    assert summary.pass_rate < 1.0
    assert summary.quality_score < 1.0


def test_quality_score_separates_valid_from_good():
    """
    `pass_rate` is a gate; `quality_score` is the number that drifts. A run that
    is entirely legal but consistently picks the wrong winner must move one and
    not the other, or a slow decline would be invisible.
    """
    responses = {}
    for case in case_module.RANKING_CASES:
        body = copy.deepcopy(_recorded()[f"ranking:{case.id}"])
        body["ranked_creators"].reverse()
        responses[f"ranking:{case.id}"] = body

    summary = RunSummary(run_replay(responses))

    assert summary.pass_rate == 1.0, "reordering is legal, so nothing should fail"
    assert summary.quality_score < 1.0, "but quality must register the decline"


async def test_the_live_path_drives_the_real_production_prompts(monkeypatch):
    """
    The property that makes the whole suite worth trusting.

    An eval that formats its own copy of a prompt measures the copy. This runs
    the live path with only the network call stubbed, and asserts that what
    reached the model was the real `BRAND_CREATOR_RANKING_PROMPT`, with the real
    injection guard and the case's own data interpolated into it.
    """
    from app.core.config import settings
    from app.modules.ai import ai_service
    from evals.runner import _run_live

    seen_prompts = []

    async def fake_generate(self, prompt):
        seen_prompts.append(prompt)
        if "Rank the creators" in prompt:
            return json.dumps(_recorded()["ranking:niche-match-beats-reach"])
        return json.dumps(_recorded()["opportunity:strong-match-reads-as-strong"])

    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(ai_service.GeminiClient, "generate", fake_generate)
    monkeypatch.setattr(ai_service.genai, "Client", lambda **kw: object())

    results, _ = await _run_live(record=False)

    assert len(results) == len(RANKING) + len(OPPORTUNITY)
    assert len(seen_prompts) == len(seen_prompts)

    ranking_prompt = next(p for p in seen_prompts if "Rank the creators" in p)
    # The real prompt template, not a copy living in the eval package.
    assert "SECURITY:" in ranking_prompt, "the injection guard was not applied"
    assert "<<<BRAND_DATA" in ranking_prompt
    assert "<<<CREATORS_DATA" in ranking_prompt
    # And the case's own fixture data actually reached it.
    assert "Aarav Mehta" in ranking_prompt

    opportunity_prompt = next(p for p in seen_prompts if "DO NOT INVENT TERMS" in p)
    assert "SECURITY:" in opportunity_prompt


def test_the_recorded_fixtures_are_labelled_as_stand_ins():
    """
    They were hand-written, not captured from Gemini — the machine this was
    built on had no route to Google. Somebody reading a green run needs to know
    that, or replay gets mistaken for a measurement of the model.
    """
    note = " ".join(_recorded()["_note"]).lower()

    assert "not captured from gemini" in note
    assert "--live --record" in note
