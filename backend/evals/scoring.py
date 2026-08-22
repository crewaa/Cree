"""
Scoring for the prompt evals.

Pure functions over a model response and a case. No network, no model, no
config — so the scorer itself is unit-testable, which matters more than it
sounds: a quality suite whose scorer is wrong reports green while the product
degrades, and nobody checks the checker.

Three grades of finding, and the distinction is the useful part:

* **violation** — the output is wrong in a way that damages a user. A Food
  creator rated "High" for a protein campaign, or a brand name reaching a
  creator. These fail the run outright, at any rate above zero.
* **miss** — the output is defensible but not what a person would have picked.
  Measured as a rate and compared against a baseline, because some drift is
  normal and only a *trend* is signal.
* **malformed** — the model returned something the parser could not use. Almost
  always a prompt edit rather than a model change.
"""

from dataclasses import dataclass, field

#: Ordered worst to best, so "at least Medium" is expressible.
FIT_ORDER = ["Low", "Medium", "High"]


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    violations: list[str] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)
    #: Free-text notes for the report — never affects pass/fail.
    notes: list[str] = field(default_factory=list)

    @property
    def is_violation(self) -> bool:
        return bool(self.violations) or bool(self.malformed)


def score_ranking(case, response: dict) -> CaseResult:
    """Grade one ranking response against its golden case."""
    result = CaseResult(case_id=case.id, passed=True)

    ranked = response.get("ranked_creators")
    if not isinstance(ranked, list) or not ranked:
        result.malformed.append("no ranked_creators list in the response")
        result.passed = False
        return result

    sent_ids = {c["creator_identity"]["id"] for c in case.creators}
    returned_ids = [str(r.get("creator_id", "")) for r in ranked]

    # A hallucinated id is a correctness bug, not a quality one: it would be
    # written into saved_creators as a real brand-creator match.
    invented = [i for i in returned_ids if i not in sent_ids]
    if invented:
        result.violations.append(f"invented creator ids: {sorted(set(invented))}")

    # Every creator sent should come back. Silently dropping candidates means a
    # brand never learns those creators exist.
    dropped = sent_ids - set(returned_ids)
    if dropped:
        result.misses.append(f"did not rank {len(dropped)} creator(s): {sorted(dropped)}")

    # Top-1: is the highest-ranked creator a defensible choice?
    if returned_ids and returned_ids[0] not in case.acceptable_top:
        result.misses.append(
            f"ranked {returned_ids[0]} first; expected one of {sorted(case.acceptable_top)}"
        )

    # Forbidden "High" ratings — the hard failure.
    for entry in ranked:
        cid = str(entry.get("creator_id", ""))
        fit = str(entry.get("fit_level", ""))
        if fit == "High" and cid in case.forbidden_high:
            result.violations.append(
                f"rated creator {cid} High, which the case forbids"
            )
        if fit and fit not in FIT_ORDER:
            result.malformed.append(f"unknown fit_level {fit!r} for creator {cid}")

    # Reasoning has to exist, or the brand is being asked to trust a bare label.
    unreasoned = [
        str(e.get("creator_id"))
        for e in ranked
        if not e.get("score_reasoning")
    ]
    if unreasoned:
        result.misses.append(f"no reasoning given for {sorted(unreasoned)}")

    result.passed = not result.is_violation
    return result


def score_opportunity(case, response: dict) -> CaseResult:
    """Grade one creator-facing opportunity assessment."""
    result = CaseResult(case_id=case.id, passed=True)

    fit = str(response.get("fit_level", ""))
    if not fit:
        result.malformed.append("no fit_level in the response")
    elif fit not in FIT_ORDER:
        result.malformed.append(f"unknown fit_level {fit!r}")
    elif fit not in case.expected_fit:
        result.misses.append(
            f"fit_level {fit}; expected one of {sorted(case.expected_fit)}"
        )

    # Anonymity. The scrubber enforces this in production; here we are checking
    # the *prompt* is not working against it.
    blob = " ".join(
        str(v) for v in _flatten(response)
    ).lower()
    for forbidden in case.forbidden_substrings:
        if forbidden.lower() in blob:
            result.violations.append(f"leaked brand identity: {forbidden!r}")

    # The model must not state commercial terms. Production strips these keys,
    # so their presence means the prompt has drifted even if users never see it.
    for key in ("compensation", "budget", "fee", "deliverables", "timeline", "deadline"):
        if key in response:
            result.violations.append(f"model returned a commercial term: {key}")

    if not response.get("why_it_fits"):
        result.misses.append("no why_it_fits — the creator gets a label with no reason")
    if not response.get("what_to_expect"):
        result.misses.append("no what_to_expect — nothing describing the work")

    result.passed = not result.is_violation
    return result


def _flatten(value, depth: int = 0):
    """Yield every scalar in a nested structure, for substring checks."""
    if depth > 6:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _flatten(v, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _flatten(item, depth + 1)
    else:
        yield value


@dataclass
class RunSummary:
    """Aggregate of one full pass over the suite."""
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def violations(self) -> int:
        return sum(1 for r in self.results if r.is_violation)

    @property
    def miss_count(self) -> int:
        return sum(len(r.misses) for r in self.results)

    @property
    def pass_rate(self) -> float:
        """Share of cases with no violations. 1.0 is the only acceptable value."""
        return 1.0 if not self.total else sum(r.passed for r in self.results) / self.total

    @property
    def quality_score(self) -> float:
        """
        Share of cases that were both valid *and* matched the human expectation.

        Separate from `pass_rate` on purpose: pass_rate is a gate, this is the
        number that drifts. A prompt change that keeps everything legal but
        starts ranking the wrong creator first moves this and not that.
        """
        if not self.total:
            return 0.0
        clean = sum(1 for r in self.results if r.passed and not r.misses)
        return clean / self.total

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "violations": self.violations,
            "misses": self.miss_count,
            "pass_rate": round(self.pass_rate, 4),
            "quality_score": round(self.quality_score, 4),
        }
