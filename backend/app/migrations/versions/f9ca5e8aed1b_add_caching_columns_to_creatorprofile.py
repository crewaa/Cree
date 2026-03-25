"""Add caching columns to CreatorProfile

Revision ID: f9ca5e8aed1b
Revises: dd173ce633c3
Create Date: 2026-03-26 00:54:08.858070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9ca5e8aed1b'
down_revision: Union[str, Sequence[str], None] = 'dd173ce633c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('creator_profiles', sa.Column('ai_summary', sa.Text(), nullable=True))
    op.add_column('creator_profiles', sa.Column('summary_generated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('creator_profiles', sa.Column('cached_brand_deals', sa.Text(), nullable=True))
    op.add_column('creator_profiles', sa.Column('brand_deals_generated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    pass
