"""add_total_vectors_and_incremental_to_embedding_jobs

Revision ID: h2m3n4o5p6q7
Revises: g7h8i9j0k1l2
Create Date: 2025-06-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h2m3n4o5p6q7'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add total_vectors and incremental columns to embedding_jobs table."""
    # Add total_vectors column with default 0
    op.add_column('embedding_jobs', sa.Column('total_vectors', sa.Integer(), nullable=False, server_default='0'))
    
    # Add incremental column with default false (0)
    op.add_column('embedding_jobs', sa.Column('incremental', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove total_vectors and incremental columns from embedding_jobs table."""
    op.drop_column('embedding_jobs', 'incremental')
    op.drop_column('embedding_jobs', 'total_vectors')
