"""remove_context_length_and_dimensions_columns

Revision ID: fbc008beb3d3
Revises: i3j4k5l6m7n8
Create Date: 2026-04-27 11:55:48.747237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbc008beb3d3'
down_revision: Union[str, Sequence[str], None] = 'i3j4k5l6m7n8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove context_length and dimensions columns."""
    # Drop the dependent view (legacy, not used by application code)
    op.execute('DROP VIEW IF EXISTS v_available_models CASCADE')
    
    # Drop the columns
    op.drop_column('ai_models', 'context_length')
    op.drop_column('ai_models', 'dimensions')


def downgrade() -> None:
    """Downgrade schema - restore context_length and dimensions columns."""
    op.add_column('ai_models', sa.Column('dimensions', sa.Integer(), nullable=True))
    op.add_column('ai_models', sa.Column('context_length', sa.Integer(), nullable=True))
