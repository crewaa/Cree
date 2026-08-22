"""
Tests for the TEXT -> JSONB migration of the AI cache columns.

**Read this before changing the migration.** The PostgreSQL half of it cannot be
executed in CI: the test suite runs on SQLite, and no PostgreSQL is available in
the environment this was written in. So the parts that *can* be tested are
tested hard, and the part that cannot is kept as small and as boring as possible
— one `ALTER COLUMN ... TYPE jsonb USING col::jsonb` per column, with every
value that could make it fail already removed by the code below.

That split matters because `ALTER ... USING col::jsonb` aborts the whole
migration if a single row holds text that is not valid JSON. On a live deploy
that is an outage with a confusing cause. These columns are caches, so a value
that cannot be parsed is worth nothing and is set to NULL first — the user
regenerates it and loses nothing but one click.
"""

import importlib.util
import json
import pathlib

import pytest
from sqlalchemy import create_engine, text

MIGRATION = (
    pathlib.Path(__file__).resolve().parents[1]
    / "app" / "migrations" / "versions" / "f7a2c4e91b35_ai_cache_to_jsonb.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("jsonb_migration", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def db(tmp_path):
    """A scratch table shaped like the real one, with the columns still TEXT."""
    engine = create_engine(f"sqlite:///{tmp_path/'m.db'}")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE creator_profiles ("
            " id INTEGER PRIMARY KEY, ai_summary TEXT, cached_brand_deals TEXT)"
        ))
    return engine


def _insert(engine, rows):
    with engine.begin() as conn:
        for row_id, summary, deals in rows:
            conn.execute(
                text("INSERT INTO creator_profiles (id, ai_summary, cached_brand_deals) "
                     "VALUES (:i, :s, :d)"),
                {"i": row_id, "s": summary, "d": deals},
            )


def _fetch(engine):
    with engine.begin() as conn:
        return {
            r[0]: (r[1], r[2])
            for r in conn.execute(
                text("SELECT id, ai_summary, cached_brand_deals FROM creator_profiles")
            )
        }


def test_valid_json_is_left_untouched(db):
    """The migration must not damage the caches it is meant to preserve."""
    summary = json.dumps({"summary": "strong engagement"})
    deals = json.dumps([{"brand_id": 1, "opportunity": {"opportunity_id": "x"}}])
    _insert(db, [(1, summary, deals)])

    migration = _load_migration()
    with db.begin() as conn:
        assert migration.null_out_unparseable(conn) == 0

    assert _fetch(db)[1] == (summary, deals)


def test_malformed_json_is_cleared_so_the_cast_cannot_fail(db):
    """
    The failure this migration is built around. One row of junk would otherwise
    abort the deploy with "invalid input syntax for type json".
    """
    _insert(db, [
        (1, "not json at all", "[{\"opportunity\": {}}]"),
        (2, "{truncated", "also junk"),
    ])

    migration = _load_migration()
    with db.begin() as conn:
        cleared = migration.null_out_unparseable(conn)

    assert cleared == 3
    rows = _fetch(db)
    assert rows[1][0] is None                      # bad summary cleared
    assert rows[1][1] == '[{"opportunity": {}}]'   # good deals preserved
    assert rows[2] == (None, None)


def test_nulls_and_empty_tables_are_handled(db):
    """A fresh install has no rows; a partial one has NULLs. Neither may raise."""
    migration = _load_migration()
    with db.begin() as conn:
        assert migration.null_out_unparseable(conn) == 0

    _insert(db, [(1, None, None)])
    with db.begin() as conn:
        assert migration.null_out_unparseable(conn) == 0


def test_an_empty_string_is_treated_as_malformed(db):
    """`''` is not valid JSON and would fail the cast just as loudly as junk."""
    _insert(db, [(1, "", "")])

    migration = _load_migration()
    with db.begin() as conn:
        assert migration.null_out_unparseable(conn) == 2

    assert _fetch(db)[1] == (None, None)


def test_the_migration_is_a_no_op_on_sqlite(db):
    """
    SQLite has neither JSONB nor `ALTER COLUMN ... TYPE`, and stores JSON as
    text anyway — so the upgrade must skip rather than fail. If this regresses,
    the whole test suite stops being able to build its schema.
    """
    migration = _load_migration()

    class _FakeOp:
        def __init__(self, conn):
            self.conn = conn
            self.altered = []

        def get_bind(self):
            return self.conn

        def alter_column(self, *args, **kwargs):
            self.altered.append((args, kwargs))

    with db.begin() as conn:
        fake = _FakeOp(conn)
        migration.op = fake
        migration.upgrade()

    assert fake.altered == [], "the migration tried to ALTER TYPE on SQLite"


def test_the_postgres_path_alters_exactly_the_two_cache_columns():
    """
    The PostgreSQL branch cannot be executed here, so assert its *intent*: which
    columns it touches, what it casts them to, and that it uses a USING clause.
    A migration that silently altered a third column would be caught here.
    """
    migration = _load_migration()
    calls = []

    class _FakePgConn:
        class dialect:
            name = "postgresql"

        def execute(self, *args, **kwargs):
            class _Empty:
                def fetchall(self_inner):
                    return []
            return _Empty()

    class _FakeOp:
        def get_bind(self):
            return _FakePgConn()

        def alter_column(self, table, column, **kwargs):
            calls.append((table, column, kwargs))

    migration.op = _FakeOp()
    migration.upgrade()

    assert [c[1] for c in calls] == ["ai_summary", "cached_brand_deals"]
    assert all(c[0] == "creator_profiles" for c in calls)
    for _, column, kwargs in calls:
        assert kwargs["postgresql_using"] == f"{column}::jsonb", (
            "without a USING clause PostgreSQL cannot cast text to jsonb"
        )
        assert kwargs["existing_nullable"] is True
