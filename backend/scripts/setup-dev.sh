#!/usr/bin/env bash
#
# Create (or recreate) the backend virtualenv and install dependencies.
#
#   cd backend && ./scripts/setup-dev.sh
#
# Safe to re-run: it removes any existing .venv first. That matters because a
# virtualenv is tied to the OS and Python version that built it — one created
# on Linux will not work on macOS.
#
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"

echo "==> Checking Python version"
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(
        f"Python 3.11+ required, found {sys.version.split()[0]}.\n"
        "Install a newer Python (e.g. `brew install python@3.12`) and re-run "
        "with: PYTHON=python3.12 ./scripts/setup-dev.sh"
    )
print(f"    Python {sys.version.split()[0]} OK")
PY

echo "==> Recreating .venv"
rm -rf .venv
"$PYTHON" -m venv .venv

echo "==> Installing dependencies"
./.venv/bin/pip install --quiet --upgrade pip setuptools wheel
./.venv/bin/pip install --quiet -e ".[dev]"

if [ ! -f .env ]; then
  echo "==> Writing a starter .env (fill in the real values)"
  cat > .env <<'ENVEOF'
# Required — the app will not boot without these.
APP_NAME=Crewaa
ENV=dev
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME
JWT_SECRET_KEY=change-me-to-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com

# Optional — the related feature is disabled when blank.
GEMINI_API_KEY=
APIFY_TOKEN=
YOUTUBE_API_KEY=

# Error tracking. Blank = disabled, which is the right setting for local dev:
# you do not want your own debugging filling up a shared issue tracker.
SENTRY_DSN=

# Optional overrides
# GEMINI_MODEL=gemini-2.5-flash
# CORS_ORIGINS=http://localhost:3000,https://crewaa.in
# SENTRY_ENVIRONMENT=production        # defaults to ENV
# SENTRY_RELEASE=$(git rev-parse --short HEAD)
# SENTRY_TRACES_SAMPLE_RATE=0.0        # performance tracing is billed separately
ENVEOF
  echo "    Created backend/.env — this file is gitignored. Fill it in before running."
else
  echo "==> backend/.env already exists, leaving it alone"
fi

echo
echo "Done. Next:"
echo "  source .venv/bin/activate"
echo "  pytest -q                      # run the test suite"
echo "  uvicorn app.main:app --reload  # start the API on :8000"
