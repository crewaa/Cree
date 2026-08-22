# Prompt evals

Anonymity and structure are covered by the normal test suite. This measures the
thing those tests cannot: **whether the matching is any good.**

Without it, a prompt edit or a Gemini model update can quietly make Crewaa worse
at its one job, and the first person to notice is a brand who paid for a
shortlist of the wrong creators.

## Running

```bash
cd backend && source .venv/bin/activate

# Free, offline, no API key. Runs in CI.
python -m evals.runner

# The real measurement. Costs Gemini quota.
python -m evals.runner --live --repeat 3

# Capture this run as the new fixtures + baseline.
python -m evals.runner --live --record
```

## The two modes, and what each can actually tell you

| | replay (default) | `--live` |
|---|---|---|
| Calls Gemini | no | yes |
| Costs quota | no | yes |
| Deterministic | yes | no |
| Runs in CI | yes | no |
| **Catches a broken prompt or parser** | yes | yes |
| **Catches the model getting worse** | **no** | yes |

Replay scores frozen responses. It cannot measure a model it never called — it
proves the pipeline still works. Treat a green replay run as "nothing is
broken", never as "the matching is good".

> **The shipped fixtures in `recorded.json` are hand-written, not captured from
> Gemini.** The environment this suite was built in had no network route to
> Google. Run `--live --record` once from a machine that does; that overwrites
> them with real output and writes a real `baseline.json`.

## Reading a live run

**Violations** fail the run at any rate above zero. A wrong-niche "High" fit, an
invented creator id, a leaked brand name, a model-stated fee.

**Misses** are defensible-but-not-ideal outputs. They move `quality_score`
without failing. This is the number to watch as a trend.

**Repeat, always.** The model is stochastic; the same prompt can rank
differently twice in a row. A single run is not evidence. `--repeat 3` reports
the spread and judges on the *worst* run — a suite that passes on its best
attempt will surprise you in production.

## Why live runs are not in CI

They cost money, they are non-deterministic, and a flaky red build teaches
people to ignore the suite — at which point it is worse than not having one.
Run it deliberately: once before changing a prompt, once after, and compare.

## Adding a case

Put it in `cases.py` with a `rationale` explaining why the expected answer is
right — written *before* you look at what the model says. Expectations derived
from current output only confirm the model still does what it did last week.

Where a trade-off is genuinely arguable, list every defensible answer in
`acceptable_top`. Demanding one answer to an ambiguous question measures
conformity, not quality.

## Files

| File | What it is |
|---|---|
| `cases.py` | The golden dataset. Read this first. |
| `scoring.py` | Pure scoring functions. Unit-tested in `tests/test_evals.py`. |
| `runner.py` | Executes cases live or from replay, aggregates, compares to baseline. |
| `recorded.json` | Frozen responses for replay. Regenerate with `--live --record`. |
| `baseline.json` | Last human-reviewed scores. Created by `--record`; not committed until a real live run exists. |

`tests/test_evals.py` tests the suite itself — mostly by feeding it output known
to be bad and asserting it goes red. An eval suite that passes everything is
worse than none, because the green tick gets trusted.
