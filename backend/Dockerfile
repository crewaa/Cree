# Crewaa backend.
#
# Build from the `backend/` directory:
#   docker build -t crewaa-backend .
#   docker run -p 8000:8000 --env-file .env crewaa-backend
#
# Configuration is supplied entirely through environment variables — no secret
# is ever baked into the image.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build tools are needed for some wheels but not at runtime, so install,
# use, and remove them in a single layer.
COPY pyproject.toml ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && pip install --upgrade pip \
    && pip install . \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY app ./app
COPY alembic.ini ./
COPY seed_admin.py ./

# Run unprivileged.
RUN useradd --create-home --uid 1000 crewaa && chown -R crewaa:crewaa /app
USER crewaa

EXPOSE 8000

# Uses the real health endpoint, which verifies database connectivity.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# NOTE: migrations are deliberately NOT run on container start. Until the
# production alembic_version is reconciled (see docs/07-risks-and-gaps.md §1),
# `alembic upgrade head` must be a explicit, supervised step.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
