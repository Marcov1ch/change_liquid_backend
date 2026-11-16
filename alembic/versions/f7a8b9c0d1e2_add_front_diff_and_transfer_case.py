"""add_front_diff_and_transfer_case

Revision ID: f7a8b9c0d1e2
Revises: a7b8c9d0e1f2
Create Date: 2026-11-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VEHICLE_COLUMNS = [
    ('differential_oil_front_interval_km', sa.Integer(), True, sa.text('50000')),
    ('differential_oil_front_notify_enabled', sa.Boolean(), True, sa.text('1')),
    ('differential_oil_front_interval_months', sa.Integer(), True, None),
    ('transfer_case_interval_km', sa.Integer(), True, sa.text('50000')),
    ('transfer_case_notify_enabled', sa.Boolean(), True, sa.text('1')),
    ('transfer_case_interval_months', sa.Integer(), True, None),
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
