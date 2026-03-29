"""Add missing caching columns to CreatorProfile

Revision ID: 8230328dad8f
Revises: 3b69128322bd
Create Date: 2026-03-27 01:11:09.012497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8230328dad8f'
down_revision: Union[str, Sequence[str], None] = 'f9ca5e8aed1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columns already added by f9ca5e8aed1b — no-op to fix broken migration chain
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('creator_profiles', 'brand_deals_generated_at')
    op.drop_column('creator_profiles', 'cached_brand_deals')
    op.drop_column('creator_profiles', 'summary_generated_at')
    op.drop_column('creator_profiles', 'ai_summary')
