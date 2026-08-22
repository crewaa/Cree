#!/usr/bin/env python
"""
Send one test error to Sentry and report whether it was accepted.

An error tracker is not installed until an event has actually arrived. The unit
tests prove the scrubbing and the wiring without a network, but only a real
event proves the DSN, the network path and the project are right.

Usage:
    cd backend && source .venv/bin/activate && python scripts/verify-sentry.py

Then open Sentry and look for an issue titled
"Crewaa test error - safe to ignore" in the crewaa-backend project.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings          # noqa: E402
from app.core.observability import init_error_tracking  # noqa: E402


def main() -> int:
    if not settings.sentry_dsn:
        print("SENTRY_DSN is not set in backend/.env — nothing to verify.")
        return 1

    # Never print the DSN itself; the project id alone identifies where this went.
    project = settings.sentry_dsn.rstrip("/").rsplit("/", 1)[-1]
    print(f"DSN found. Sending a test event to project id {project}...")

    if not init_error_tracking():
        print("init_error_tracking() returned False — is sentry-sdk installed?")
        return 1

    import sentry_sdk

    # A password and an API key are deliberately placed in the local scope. If
    # the configuration is right, neither reaches Sentry — check the issue and
    # confirm you cannot see them anywhere on it.
    fake_password = "canary-" + "PASSWORD-must-not-appear"   # noqa: F841
    fake_api_key = "canary-" + "APIKEY-must-not-appear"      # noqa: F841

    try:
        raise RuntimeError("Crewaa test error - safe to ignore")
    except RuntimeError as exc:
        event_id = sentry_sdk.capture_exception(exc)

    delivered = sentry_sdk.flush(timeout=15)  # noqa: F841

    if not event_id:
        print("No event id was produced. The SDK did not accept the event.")
        return 1

    print(f"Event {event_id} sent.")
    print()
    print("Now open Sentry -> crewaa-backend -> Issues and confirm:")
    print("  1. an issue titled 'Crewaa test error - safe to ignore' exists")
    print("  2. the words 'canary-PASSWORD' and 'canary-APIKEY' appear NOWHERE on it")
    print()
    print("If the issue is there and the canaries are not, error tracking is")
    print("working and is not leaking local variables. Delete the issue after.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
