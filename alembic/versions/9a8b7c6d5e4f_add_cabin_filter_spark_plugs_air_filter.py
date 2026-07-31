"""add_cabin_filter_spark_plugs_air_filter

Revision ID: 9a8b7c6d5e4f
Revises: 8535173598fd
Create Date: 2026-07-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, Sequence[str], None] = '8535173598fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    veh_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]

    vehicle_cols = [
        ('cabin_filter_interval_km', sa.Integer(), True, sa.text('15000')),
        ('cabin_filter_notify_enabled', sa.Boolean(), False, sa.text('1')),
        ('cabin_filter_interval_months', sa.Integer(), True, None),
        ('spark_plugs_interval_km', sa.Integer(), True, sa.text('45000')),
        ('spark_plugs_notify_enabled', sa.Boolean(), False, sa.text('1')),
        ('spark_plugs_interval_months', sa.Integer(), True, None),
        ('air_filter_interval_km', sa.Integer(), True, sa.text('10000')),
        ('air_filter_notify_enabled', sa.Boolean(), False, sa.text('1')),
        ('air_filter_interval_months', sa.Integer(), True, None),
    ]
    for col_name, col_type, nullable, server_default in vehicle_cols:
        if col_name not in veh_columns:
            op.add_column('vehicles', sa.Column(col_name, type_=col_type, nullable=nullable, server_default=server_default))


def downgrade() -> None:
    conn = op.get_bind()
    veh_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]

    for col_name in [
        'cabin_filter_interval_km', 'cabin_filter_notify_enabled', 'cabin_filter_interval_months',
        'spark_plugs_interval_km', 'spark_plugs_notify_enabled', 'spark_plugs_interval_months',
        'air_filter_interval_km', 'air_filter_notify_enabled', 'air_filter_interval_months',
    ]:
        if col_name in veh_columns:
            op.drop_column('vehicles', col_name)
