"""Add saved_creators table

Revision ID: ede20de67a7b
Revises: c4a1b2d9e6f0
Create Date: 2026-03-26 00:25:51.165472

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ede20de67a7b'
down_revision: Union[str, Sequence[str], None] = 'c4a1b2d9e6f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'saved_creators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=False),
        sa.Column('fit_level', sa.String(), nullable=False),
        sa.Column('score_reasoning', sa.Text(), nullable=True),
        sa.Column('saved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['brand_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_creators_brand_id'), 'saved_creators', ['brand_id'], unique=False)
    op.create_index(op.f('ix_saved_creators_creator_id'), 'saved_creators', ['creator_id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_saved_creators_creator_id'), table_name='saved_creators')
    op.drop_index(op.f('ix_saved_creators_brand_id'), table_name='saved_creators')
    op.drop_table('saved_creators')
