"""add_tire_set_archive

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-11-09 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b3c4d5e6f7a'
down_revision: Union[str, Sequence[str], None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tire_sets',
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='0'),
    )
    op.add_column(
        'tire_sets',
        sa.Column('archived_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('tire_sets', 'archived_at')
    op.drop_column('tire_sets', 'is_archived')
