"""
Run the prompt evals.

    # Against the real model (needs GEMINI_API_KEY, costs quota):
    python -m evals.runner --live --repeat 3

    # Against recorded responses — free, offline, runs in CI:
    python -m evals.runner

    # Record fresh responses to become the new offline fixtures:
    python -m evals.runner --live --record

Two modes, because they answer different questions.

**Replay** (default) reads recorded model output and scores it. It cannot tell
you the model got worse — the responses are frozen. What it does catch, on every
CI run and for free, is a *prompt or parser* change that breaks the pipeline:
someone edits a prompt and the output stops parsing, or the anonymity scrubbing
is removed and a recorded brand name suddenly comes through.

**Live** is the actual quality measurement, and it is the one that needs
judgement to read. Two properties matter:

* **Repetition.** The model is stochastic. One run of one case tells you almost
  nothing — the same prompt can rank differently twice in a row. `--repeat`
  runs the whole suite N times and reports the spread, so a real regression can
  be told apart from noise.
* **A committed baseline.** `baseline.json` is what the suite scored when it was
  last reviewed by a person. A live run compares against it and reports the
  delta. Without that, "82% quality" is a number with nothing to be worse than.

Live runs are deliberately not wired into CI: they cost money, they are
non-deterministic, and a flaky red build trains people to ignore the suite.
Run one before changing a prompt and after, and compare.
"""

import argparse
import asyncio
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from evals import cases as case_module  # noqa: E402
from evals.scoring import RunSummary, score_opportunity, score_ranking  # noqa: E402

EVAL_DIR = pathlib.Path(__file__).resolve().parent
RECORDED = EVAL_DIR / "recorded.json"
BASELINE = EVAL_DIR / "baseline.json"

#: A live run scoring more than this far below the baseline is a regression
#: worth investigating rather than noise. Chosen to be wider than the run-to-run
#: spread observed when recording the baseline.
REGRESSION_TOLERANCE = 0.15


# ---------------------------------------------------------------------------
# Model access
# ---------------------------------------------------------------------------

async def _run_live(record: bool) -> tuple[list, dict]:
    """Execute every case against the real Gemini API."""
    from app.modules.ai.ai_service import (
        BrandCreatorRankingEngine, CampaignOpportunityEngine,
    )

    results, transcript = [], {}
    ranking_engine = BrandCreatorRankingEngine()
    opportunity_engine = CampaignOpportunityEngine()

    for case in case_module.RANKING_CASES:
        response = await ranking_engine.rank_creators(case.brand_data, case.creators)
        if record:
            transcript[f"ranking:{case.id}"] = response
        results.append(score_ranking(case, response))

    for case in case_module.OPPORTUNITY_CASES:
        response = await opportunity_engine.assess(case.campaign_data, case.creator_data)
        if record:
            transcript[f"opportunity:{case.id}"] = response
        results.append(score_opportunity(case, response))

    return results, transcript


def run_replay(recorded: dict | None = None) -> list:
    """
    Score previously recorded responses. No model, no network, no key.

    Exposed as a plain function rather than hidden behind the CLI so the test
    suite can call it directly.
    """
    if recorded is None:
        recorded = json.loads(RECORDED.read_text()) if RECORDED.exists() else {}

    results = []
    for case in case_module.RANKING_CASES:
        response = recorded.get(f"ranking:{case.id}")
        if response is not None:
            results.append(score_ranking(case, response))

    for case in case_module.OPPORTUNITY_CASES:
        response = recorded.get(f"opportunity:{case.id}")
        if response is not None:
            results.append(score_opportunity(case, response))

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def format_report(summary: RunSummary, label: str) -> str:
    lines = [
        "",
        f"  {label}",
        f"  {'-' * len(label)}",
        f"  cases          {summary.total}",
        f"  violations     {summary.violations}"
        + ("   <-- must be 0" if summary.violations else ""),
        f"  misses         {summary.miss_count}",
        f"  pass rate      {summary.pass_rate:.0%}",
        f"  quality score  {summary.quality_score:.0%}",
    ]

    for result in summary.results:
        if not result.violations and not result.misses and not result.malformed:
            continue
        lines.append(f"\n  {result.case_id}")
        for v in result.violations:
            lines.append(f"     VIOLATION  {v}")
        for m in result.malformed:
            lines.append(f"     MALFORMED  {m}")
        for m in result.misses:
            lines.append(f"     miss       {m}")

    return "\n".join(lines) + "\n"


def compare_to_baseline(summary: RunSummary) -> tuple[bool, str]:
    """Report movement against the last human-reviewed run."""
    if not BASELINE.exists():
        return True, "  no baseline recorded yet — run with --record to create one\n"

    baseline = json.loads(BASELINE.read_text())
    before = baseline.get("quality_score", 0.0)
    after = summary.quality_score
    delta = after - before

    line = (
        f"  baseline quality {before:.0%} -> now {after:.0%} "
        f"({delta:+.0%}), recorded {baseline.get('recorded_at', 'unknown')}\n"
    )
    if delta < -REGRESSION_TOLERANCE:
        return False, line + (
            f"  REGRESSION: quality fell more than {REGRESSION_TOLERANCE:.0%} "
            "below the baseline.\n"
        )
    return True, line


def main() -> int:
    parser = argparse.ArgumentParser(description="Crewaa prompt evals")
    parser.add_argument("--live", action="store_true",
                        help="call the real Gemini API (costs quota)")
    parser.add_argument("--repeat", type=int, default=1,
                        help="run the suite N times; the model is stochastic")
    parser.add_argument("--record", action="store_true",
                        help="save this run's responses and score as the new baseline")
    args = parser.parse_args()

    if args.record and not args.live:
        print("--record only makes sense with --live", file=sys.stderr)
        return 2

    runs, transcript = [], {}
    for attempt in range(args.repeat):
        if args.live:
            results, captured = asyncio.run(_run_live(record=args.record))
            transcript = captured or transcript
        else:
            results = run_replay()

        if not results:
            print("No cases scored. Is recorded.json missing?", file=sys.stderr)
            return 2

        summary = RunSummary(results)
        runs.append(summary)
        label = f"run {attempt + 1}/{args.repeat}" + (" (live)" if args.live else " (replay)")
        print(format_report(summary, label))

    scores = [r.quality_score for r in runs]
    worst = min(runs, key=lambda r: r.quality_score)

    if args.repeat > 1:
        spread = statistics.pstdev(scores) if len(scores) > 1 else 0.0
        print(f"  across {args.repeat} runs: mean {statistics.mean(scores):.0%}, "
              f"spread +/-{spread:.0%}, worst {min(scores):.0%}\n")

    # Judge on the worst run. A suite that passes on its best attempt is a suite
    # that will surprise you in production.
    ok, comparison = compare_to_baseline(worst)
    print(comparison)

    if args.record:
        RECORDED.write_text(json.dumps(transcript, indent=2, sort_keys=True) + "\n")
        BASELINE.write_text(json.dumps(
            {**worst.as_dict(), "recorded_at": _today(), "repeat": args.repeat},
            indent=2, sort_keys=True,
        ) + "\n")
        print(f"  recorded {len(transcript)} responses and a new baseline\n")
        return 0

    if worst.violations:
        print("  FAILED: violations are never acceptable\n")
        return 1
    if not ok:
        return 1

    print("  OK\n")
    return 0


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
