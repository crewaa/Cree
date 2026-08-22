"""
Shared test fixtures.

Tests run against a real SQLite database created fresh per test, so they
exercise actual SQL and actual FastAPI dependency wiring rather than mocks.
Nothing here touches the network or a real Postgres instance.

Environment variables are set before importing any app module, because
`app.core.config.Settings` validates at import time and `app.core.database`
creates the engine at import time.
"""

import os
import tempfile

os.environ.setdefault("APP_NAME", "Crewaa-Test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-used-anywhere-real")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

# Forced empty, not `setdefault`: `Settings` also reads `backend/.env`, which on
# a real machine holds the live DSN. Without this line every local `pytest` run
# would report its deliberate failures to the production Sentry project and eat
# the 5k/month quota. Tests that need a live client build their own (see
# tests/test_observability.py) — no test may ever use the real one.
os.environ["SENTRY_DSN"] = ""

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.common.dependencies import get_db  # noqa: E402
from app.common.rate_limit import reset_for_tests  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import *  # noqa: E402,F401,F403  (registers every mapper)
from app.modules.users.models import BrandProfile, CreatorProfile, User  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Rate limits are process-global; reset between tests."""
    reset_for_tests()
    yield
    reset_for_tests()


@pytest.fixture(autouse=True)
def _no_real_scrapes(monkeypatch):
    """
    Stop HTTP tests from kicking off real background scrapes.

    The scrape routes queue a BackgroundTask which opens its own session against
    the configured DATABASE_URL — not the per-test database — and would call
    Apify / the YouTube API for real. Patching the names as imported into the
    route modules leaves the underlying functions intact, so tests that exercise
    the scrapers directly still get the real implementation.
    """
    async def noop(*args, **kwargs):
        return {"status": "success", "message": "stubbed in tests"}

    monkeypatch.setattr(
        "app.modules.instagram.routes.instagram.scrape_and_store", noop, raising=False
    )
    monkeypatch.setattr(
        "app.modules.youtube.routes.scrape_and_store_youtube", noop, raising=False
    )
    monkeypatch.setattr(
        "app.modules.users.router.scrape_and_store", noop, raising=False
    )
    monkeypatch.setattr(
        "app.modules.users.router.scrape_and_store_youtube", noop, raising=False
    )


@pytest_asyncio.fixture
async def session_factory():
    """A fresh SQLite database per test, backed by a temp file."""
    # A bare `:memory:` URL was tried first and is wrong for concurrency
    # tests: SQLAlchemy's default async pool opens a new physical connection
    # per concurrent checkout, and each `:memory:` connection is its own
    # separate, isolated database — so concurrent signups for the same email
    # could land on different empty databases and both "win". Forcing every
    # checkout onto one shared connection (`poolclass=StaticPool`) was tried
    # next and is also wrong: concurrent AsyncSessions then share one
    # DBAPI-level transaction, so a second session's uncommitted insert
    # becomes visible to a first session that hasn't committed yet, and both
    # could get past the pre-check and insert.
    #
    # A temp file, left on the default pool (a real connection per checkout)
    # with a busy timeout, is what makes this behave like production
    # Postgres: independent connections, and SQLite's own file write-lock
    # serialises concurrent writers instead of erroring immediately, giving
    # the loser of a race a real IntegrityError on its own connection rather
    # than corrupted shared transaction state.
    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )

    # SQLite ignores foreign keys unless asked. Without this, ON DELETE CASCADE
    # never fires and cascade tests would pass vacuously.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()
    os.remove(db_path)


@pytest_asyncio.fixture
async def client(session_factory):
    """HTTP client with the app's DB dependency pointed at the test database."""

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User factories
# ---------------------------------------------------------------------------

async def make_user(
    session_factory,
    email: str,
    role: str,
    password: str | None = "correct-horse-battery",
    is_active: bool = True,
) -> User:
    async with session_factory() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password) if password else None,
            role=role,
            is_active=is_active,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


async def make_creator_profile(session_factory, user_id: int, **overrides) -> CreatorProfile:
    fields = {
        "full_name": "Test Creator",
        "location": "Mumbai",
        "primary_platform": "Instagram",
        "category": "Fitness",
        "instagram_username": "testcreator",
    }
    fields.update(overrides)

    async with session_factory() as db:
        profile = CreatorProfile(user_id=user_id, **fields)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile


async def make_brand_profile(session_factory, user_id: int, **overrides) -> BrandProfile:
    fields = {"brand_name": "Acme Corp", "industry": "Fitness"}
    fields.update(overrides)

    async with session_factory() as db:
        profile = BrandProfile(user_id=user_id, **fields)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "role": user.role}, 60)
    return {"Authorization": f"Bearer {token}"}
