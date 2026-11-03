"""add_vehicle_share_token

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _vehicle_columns() -> list:
    conn = op.get_bind()
    return [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    rows = conn.execute(sa.text("PRAGMA index_list(vehicles)")).fetchall()
    return any(row[1] == name for row in rows)


def upgrade() -> None:
    existing = _vehicle_columns()

    if 'share_token' not in existing:
        op.add_column('vehicles', sa.Column('share_token', sa.String(), nullable=True))

    if not _index_exists('ix_vehicles_share_token'):
        op.create_index(
            'ix_vehicles_share_token',
            'vehicles',
            ['share_token'],
            unique=True,
        )


def downgrade() -> None:
    existing = _vehicle_columns()

    if 'share_token' in existing:
        if _index_exists('ix_vehicles_share_token'):
            op.drop_index('ix_vehicles_share_token', table_name='vehicles')
        op.drop_column('vehicles', 'share_token')
