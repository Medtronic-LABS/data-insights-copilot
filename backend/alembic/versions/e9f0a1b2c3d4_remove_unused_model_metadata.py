"""remove_unused_model_metadata

Revision ID: e9f0a1b2c3d4
Revises: fbc008beb3d3
Create Date: 2026-04-27 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'fbc008beb3d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove unused model metadata columns."""
    # Drop the unused columns
    op.drop_column('ai_models', 'hf_revision')
    op.drop_column('ai_models', 'max_input_tokens')
    op.drop_column('ai_models', 'recommended_chunk_size')
    op.drop_column('ai_models', 'compatibility_notes')


def downgrade() -> None:
    """Downgrade schema - restore unused model metadata columns."""
    op.add_column('ai_models', sa.Column('compatibility_notes', sa.Text(), nullable=True))
    op.add_column('ai_models', sa.Column('recommended_chunk_size', sa.Integer(), nullable=True))
    op.add_column('ai_models', sa.Column('max_input_tokens', sa.Integer(), nullable=True))
    op.add_column('ai_models', sa.Column('hf_revision', sa.String(100), nullable=True))
