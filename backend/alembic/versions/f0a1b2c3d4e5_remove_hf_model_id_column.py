"""remove_hf_model_id_column

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-04-27 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e9f0a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - remove hf_model_id column (can be derived from model_id)."""
    op.drop_column('ai_models', 'hf_model_id')


def downgrade() -> None:
    """Downgrade schema - restore hf_model_id column."""
    op.add_column('ai_models', sa.Column('hf_model_id', sa.String(500), nullable=True))
