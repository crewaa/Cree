"""Restore saved_creators, and add the missing uniqueness guarantee

Repairs the damage from revision dd173ce633c3, which was titled
"Add caching columns to CreatorProfile" but whose upgrade() actually dropped the
`saved_creators` table. That revision has now been neutralised to a no-op, but
any database that already ran it is missing the table.

This revision is deliberately IDEMPOTENT. It inspects the live schema and only
creates what is absent, so it is safe to run against:

  - production, which (probably) still has the table  -> no-op
  - a database that lost the table                    -> recreates it
  - a brand-new database built from scratch           -> creates it

It also adds the unique constraint on (brand_id, creator_id) that the model
always implied but never had. Application code in ai/router.py dedupes in
Python by pre-loading existing rows, which races under concurrent discovery
runs by the same brand. Duplicates are collapsed before the constraint is
applied so this cannot fail on existing data.

Revision ID: b7e4c1a90f22
Revises: cee76db5231d
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7e4c1a90f22"
down_revision: Union[str, Sequence[str], None] = "cee76db5231d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE = "saved_creators"
UNIQUE_NAME = "uq_saved_creators_brand_creator"


def _inspector():
    return sa.inspect(op.get_bind())


def _dedupe_existing_rows() -> None:
    """Keep only the most recent row per (brand_id, creator_id) pair."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                f"""
                DELETE FROM {TABLE} a
                USING {TABLE} b
                WHERE a.brand_id = b.brand_id
                  AND a.creator_id = b.creator_id
                  AND a.id < b.id
                """
            )
        )
    else:
        bind.execute(
            sa.text(
                f"""
                DELETE FROM {TABLE}
                WHERE id NOT IN (
                    SELECT MAX(id) FROM {TABLE} GROUP BY brand_id, creator_id
                )
                """
            )
        )


def upgrade() -> None:
    inspector = _inspector()
    table_missing = TABLE not in inspector.get_table_names()

    if table_missing:
        # Fresh create: declare the unique constraint inline. SQLite cannot ALTER
        # a table to add a constraint, and this is the path new environments and
        # the test suite take.
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("brand_id", sa.Integer(), nullable=False),
            sa.Column("creator_id", sa.Integer(), nullable=False),
            sa.Column("fit_level", sa.String(), nullable=False),
            sa.Column("score_reasoning", sa.Text(), nullable=True),
            sa.Column(
                "saved_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["brand_id"], ["users.id"],
                name="saved_creators_brand_id_fkey", ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["creator_id"], ["users.id"],
                name="saved_creators_creator_id_fkey", ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name="saved_creators_pkey"),
            sa.UniqueConstraint("brand_id", "creator_id", name=UNIQUE_NAME),
        )

    # Refresh: the table may have just been created.
    inspector = _inspector()
    existing_indexes = {ix["name"] for ix in inspector.get_indexes(TABLE)}

    if "ix_saved_creators_brand_id" not in existing_indexes:
        op.create_index("ix_saved_creators_brand_id", TABLE, ["brand_id"], unique=False)
    if "ix_saved_creators_creator_id" not in existing_indexes:
        op.create_index("ix_saved_creators_creator_id", TABLE, ["creator_id"], unique=False)

    if not table_missing:
        # Repair path: the table survived (this is what production should hit),
        # so the constraint has to be added to a populated table.
        existing_uniques = {uc["name"] for uc in inspector.get_unique_constraints(TABLE)}
        if UNIQUE_NAME not in existing_uniques:
            _dedupe_existing_rows()
            # batch_alter_table is a plain ALTER on PostgreSQL and a
            # copy-and-move on SQLite, so this works on both.
            with op.batch_alter_table(TABLE) as batch_op:
                batch_op.create_unique_constraint(
                    UNIQUE_NAME, ["brand_id", "creator_id"]
                )


def downgrade() -> None:
    # Only the constraint this revision introduced is removed. The table itself
    # is left in place: dropping it is what caused the original incident.
    inspector = _inspector()
    if TABLE in inspector.get_table_names():
        existing_uniques = {uc["name"] for uc in inspector.get_unique_constraints(TABLE)}
        if UNIQUE_NAME in existing_uniques:
            op.drop_constraint(UNIQUE_NAME, TABLE, type_="unique")
