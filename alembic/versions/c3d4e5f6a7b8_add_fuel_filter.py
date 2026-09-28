"""add_fuel_filter

Revision ID: c3d4e5f6a7b8
Revises: 0f1a2b3c4d5e
Create Date: 2026-09-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = '0f1a2b3c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VEHICLE_COLUMNS = [
    ('fuel_filter_interval_km', sa.Integer(), True, sa.text('50000')),
    ('fuel_filter_notify_enabled', sa.Boolean(), False, sa.text('1')),
    ('fuel_filter_interval_months', sa.Integer(), True, None),
]


def _vehicle_columns() -> list:
    conn = op.get_bind()
    return [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]


def upgrade() -> None:
    existing = _vehicle_columns()

    for col_name, col_type, nullable, server_default in _VEHICLE_COLUMNS:
        if col_name not in existing:
            op.add_column('vehicles', sa.Column(
                col_name,
                type_=col_type,
                nullable=nullable,
                server_default=server_default,
            ))


def downgrade() -> None:
    existing = _vehicle_columns()

    for col_name, _, _, _ in reversed(_VEHICLE_COLUMNS):
        if col_name in existing:
            op.drop_column('vehicles', col_name)
