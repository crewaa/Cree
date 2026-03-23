"""create brand profiles

Revision ID: c4a1b2d9e6f0
Revises: 3fbacdf46b79
Create Date: 2026-03-08 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4a1b2d9e6f0"
down_revision: Union[str, Sequence[str], None] = "3fbacdf46b79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("brand_name", sa.String(), nullable=False),
        sa.Column("industry", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(), nullable=True),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.Column("campaign_goal", sa.String(), nullable=False),
        sa.Column("budget_range", sa.String(), nullable=False),
        sa.Column("target_location", sa.String(), nullable=True),
        sa.Column("target_languages", sa.Text(), nullable=True),
        sa.Column("platform_preferences", sa.Text(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("brand_profiles")
