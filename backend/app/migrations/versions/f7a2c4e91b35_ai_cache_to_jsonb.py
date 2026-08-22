"""Move the AI cache columns from TEXT to JSONB

Revision ID: f7a2c4e91b35
Revises: c3f5a71b8e40
Create Date: 2026-08-13

`creator_profiles.ai_summary` and `creator_profiles.cached_brand_deals` held
JSON encoded as text, so anything wanting to ask a question of them — "how many
creators matched a Fitness campaign", "which summaries mention a niche we have
no brands for" — had to load every row and parse it in Python. JSONB is
queryable and indexable.

Two deliberate choices here:

**Malformed rows are cleaned before the type change, not during it.**
`ALTER COLUMN ... USING col::jsonb` fails the entire migration if a single row
holds something that is not valid JSON — and one bad row would then block the
deploy with no obvious cause. These columns are *caches*: a value that cannot be
parsed is worth nothing, and dropping it costs the user one regeneration. So
invalid values are set to NULL first, in Python, where a parse failure is
catchable.

**SQLite is a no-op.** The test suite builds this schema on SQLite, which has no
JSONB and no `ALTER COLUMN ... TYPE`. SQLite stores JSON as TEXT regardless, so
the existing columns already hold exactly what the ORM will read back.
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f7a2c4e91b35"
down_revision = "c3f5a71b8e40"
branch_labels = None
depends_on = None

_COLUMNS = ("ai_summary", "cached_brand_deals")


def null_out_unparseable(bind) -> int:
    """
    Set any value that is not valid JSON to NULL, so the cast cannot fail.

    Done row by row through Python rather than in SQL because PostgreSQL has no
    portable "is this valid JSON" predicate before 16, and guessing with a regex
    would either miss cases or discard good data.

    Deliberately written with portable SQL (an expanding `IN`, not `= ANY`) and
    exported rather than private, so it can be tested against SQLite. The
    PostgreSQL half of this migration cannot be exercised in CI, and an
    untested data migration on a live table is how this repository lost its
    `saved_creators` table once already.

    Returns the number of rows cleared.
    """
    cleared = 0

    for column in _COLUMNS:
        rows = bind.execute(
            sa.text(
                f"SELECT id, {column} FROM creator_profiles "  # noqa: S608 - fixed names
                f"WHERE {column} IS NOT NULL"
            )
        ).fetchall()

        bad_ids = []
        for row_id, raw in rows:
            if raw is None:
                continue
            try:
                json.loads(raw)
            except (TypeError, ValueError):
                bad_ids.append(row_id)

        if bad_ids:
            statement = sa.text(
                f"UPDATE creator_profiles SET {column} = NULL WHERE id IN :ids"
            ).bindparams(sa.bindparam("ids", expanding=True))
            bind.execute(statement, {"ids": bad_ids})
            cleared += len(bad_ids)

    return cleared


def upgrade() -> None:
    bind = op.get_bind()

    # SQLite already stores these as text and the ORM's JSON type reads text
    # back, so there is nothing to convert and no ALTER TYPE to perform.
    if bind.dialect.name != "postgresql":
        return

    null_out_unparseable(bind)

    for column in _COLUMNS:
        op.alter_column(
            "creator_profiles",
            column,
            existing_type=sa.Text(),
            type_=postgresql.JSONB(astext_type=sa.Text()),
            existing_nullable=True,
            postgresql_using=f"{column}::jsonb",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for column in _COLUMNS:
        op.alter_column(
            "creator_profiles",
            column,
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            type_=sa.Text(),
            existing_nullable=True,
            postgresql_using=f"{column}::text",
        )
