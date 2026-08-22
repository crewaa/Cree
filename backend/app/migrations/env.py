from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.core.database import Base

from app.models import *

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


#: Async drivers the app may use, mapped to their synchronous equivalent.
#: Alembic runs synchronously, so the driver has to be swapped.
_SYNC_DRIVERS = {
    "+asyncpg": "+psycopg2",
    "+aiosqlite": "",
}


def _migration_db_url() -> str:
    """
    Build the Alembic connection URL from DATABASE_URL.

    The URL is read from the environment so that no credential is ever written
    into alembic.ini.

    '%' is escaped because ConfigParser performs interpolation on this value.
    """
    url = settings.database_url
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Alembic cannot run without it. "
            "Set it in backend/.env or the environment."
        )

    for async_driver, sync_driver in _SYNC_DRIVERS.items():
        if async_driver in url:
            url = url.replace(async_driver, sync_driver)
            if sync_driver == "+psycopg2":
                url = url.replace("ssl=require", "sslmode=require")
            break

    return url.replace("%", "%%")


config.set_main_option("sqlalchemy.url", _migration_db_url())

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
