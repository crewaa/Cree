"""
Guards that the migrations and the ORM models stay in agreement.

The existing CI check only compared *table names*, which is why a real
divergence went unnoticed: `saved_creators.saved_at` used
`server_default=func.now()`, compiling to a literal `now()` in the DDL.
PostgreSQL has that function, SQLite does not — so every environment built from
migrations (the test database, CI, any local SQLite setup) raised
"unknown function: now()" on the first insert, while `create_all` worked fine.

These tests compare columns and exercise the insert, so the same class of
mistake fails the build instead of surfacing during a walkthrough.
"""

import pathlib

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.database import Base
from app.models import *  # noqa: F401,F403  (registers every mapper)

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _build_from_migrations(db_path: pathlib.Path) -> None:
    """
    Run the real migration chain into a scratch SQLite file.

    `app/migrations/env.py` deliberately derives the URL from settings so no
    credential can live in alembic.ini — which means setting `sqlalchemy.url`
    on the Config here would be ignored. Point settings at the scratch file for
    the duration instead.
    """
    from app.core.config import settings

    original = settings.database_url
    settings.database_url = f"sqlite+aiosqlite:///{db_path}"
    try:
        cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_ROOT / "app" / "migrations"))
        command.upgrade(cfg, "head")
    finally:
        settings.database_url = original


@pytest.fixture(scope="module")
def migrated_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("schema") / "migrated.db"
    _build_from_migrations(db_path)
    return db_path


def test_migrations_produce_every_table_the_models_declare(migrated_db):
    engine = create_engine(f"sqlite:///{migrated_db}")
    actual = set(inspect(engine).get_table_names()) - {"alembic_version"}
    expected = set(Base.metadata.tables)

    assert not (expected - actual), f"Missing tables after upgrade: {sorted(expected - actual)}"
    assert not (actual - expected), f"Unexpected tables after upgrade: {sorted(actual - expected)}"


def test_migrations_produce_every_column_the_models_declare(migrated_db):
    """Column-level parity — the check the table-name comparison missed."""
    engine = create_engine(f"sqlite:///{migrated_db}")
    inspector = inspect(engine)

    problems = []
    for table_name, table in Base.metadata.tables.items():
        actual = {c["name"] for c in inspector.get_columns(table_name)}
        expected = {c.name for c in table.columns}
        if expected - actual:
            problems.append(f"{table_name} missing {sorted(expected - actual)}")
        if actual - expected:
            problems.append(f"{table_name} has extra {sorted(actual - expected)}")

    assert not problems, "Schema drift between migrations and models: " + "; ".join(problems)


def test_server_defaults_are_portable(migrated_db):
    """
    No DDL default may reference a function SQLite lacks.

    `now()` is the specific offender that shipped; this catches its relatives
    before they reach an environment that cannot execute them.
    """
    engine = create_engine(f"sqlite:///{migrated_db}")
    inspector = inspect(engine)

    offenders = []
    for table_name in Base.metadata.tables:
        for col in inspector.get_columns(table_name):
            default = str(col.get("default") or "")
            if "now()" in default.lower().replace(" ", ""):
                offenders.append(f"{table_name}.{col['name']} -> {default}")

    assert not offenders, (
        "Non-portable server default (use CURRENT_TIMESTAMP): " + "; ".join(offenders)
    )


def test_insert_works_against_the_migrated_schema(migrated_db):
    """
    End-to-end proof: an insert that relies on the server default must succeed.

    This is what actually failed in production-shaped testing — the schema
    looked correct, but writing a row raised `unknown function: now()`.
    """
    engine = create_engine(f"sqlite:///{migrated_db}")
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO users (id, email, role, is_active) "
            "VALUES (901, 'brand@example.com', 'BRAND', 1)"
        ))
        conn.execute(text(
            "INSERT INTO users (id, email, role, is_active) "
            "VALUES (902, 'creator@example.com', 'INFLUENCER', 1)"
        ))
        # saved_at deliberately omitted so the server default is exercised.
        conn.execute(text(
            "INSERT INTO saved_creators (brand_id, creator_id, fit_level) "
            "VALUES (901, 902, 'High')"
        ))

        saved_at = conn.execute(
            text("SELECT saved_at FROM saved_creators WHERE brand_id = 901")
        ).scalar()

    assert saved_at is not None, "server default did not populate saved_at"
