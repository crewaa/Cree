from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _engine_kwargs(url: str) -> dict:
    """
    Driver-specific engine options.

    Neon requires TLS, but `ssl=require` is an asyncpg-specific connect arg —
    passing it to any other driver raises at connect time. Previously it was
    hard-coded, which made it impossible to point the app at SQLite for tests.
    """
    kwargs: dict = {"echo": False}

    if url.startswith("postgresql+asyncpg"):
        # command_timeout bounds a single query: on Neon's free tier a cold
        # compute resume or a stuck query previously had no ceiling and could
        # hold a pool slot indefinitely, queuing every other request behind it.
        kwargs["connect_args"] = {"ssl": "require", "command_timeout": 15}
        # Neon closes idle connections; without pre-ping the first query after an
        # idle period fails with a stale-connection error instead of reconnecting.
        kwargs["pool_pre_ping"] = True
        # Render's free tier runs a single small instance — keep the pool small
        # and fail fast (rather than queuing forever) if it's exhausted.
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 5
        kwargs["pool_timeout"] = 10
    elif url.startswith("sqlite"):
        # Used by the test suite only.
        kwargs["connect_args"] = {"check_same_thread": False}

    return kwargs


engine = create_async_engine(settings.database_url, **_engine_kwargs(settings.database_url))

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
