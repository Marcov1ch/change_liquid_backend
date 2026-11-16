"""add_primary_vehicle

Revision ID: d5e6f7a8b9c0
Revises: b3c4d5e6f7a8
Create Date: 2026-11-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _user_columns() -> list:
    conn = op.get_bind()
    return [col.name for col in conn.execute(sa.text("PRAGMA table_info(users)")).fetchall()]


def upgrade() -> None:
    existing = _user_columns()
    if 'primary_vehicle_id' not in existing:
        op.add_column('users', sa.Column('primary_vehicle_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    existing = _user_columns()
    if 'primary_vehicle_id' in existing:
        op.drop_column('users', 'primary_vehicle_id')
