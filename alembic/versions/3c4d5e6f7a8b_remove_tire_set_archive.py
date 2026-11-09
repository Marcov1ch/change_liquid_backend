"""remove_tire_set_archive

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-11-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3c4d5e6f7a8b'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tire_sets') as batch_op:
        batch_op.drop_column('archived_at')
        batch_op.drop_column('is_archived')


def downgrade() -> None:
    with op.batch_alter_table('tire_sets') as batch_op:
        batch_op.add_column(
            sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='0'),
        )
        batch_op.add_column(
            sa.Column('archived_at', sa.DateTime(), nullable=True),
        )
