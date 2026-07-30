"""add_date_tracking_columns

Revision ID: 8535173598fd
Revises: 179ecac9b418
Create Date: 2026-07-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8535173598fd'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- vehicles ---
    veh_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]

    vehicle_cols = [
        ('oil_interval_months', sa.Integer(), True, None),
        ('transmission_interval_months', sa.Integer(), True, None),
        ('brake_interval_months', sa.Integer(), True, None),
        ('coolant_interval_months', sa.Integer(), True, None),
        ('power_steering_interval_months', sa.Integer(), True, None),
        ('differential_oil_interval_months', sa.Integer(), True, None),
        ('tire_notify_enabled', sa.Boolean(), False, sa.text('1')),
    ]
    for col_name, col_type, nullable, server_default in vehicle_cols:
        if col_name not in veh_columns:
            op.add_column('vehicles', sa.Column(col_name, type_=col_type, nullable=nullable, server_default=server_default))

    # --- replacements ---
    rep_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(replacements)")).fetchall()]

    replacements_cols = [
        ('interval_months', sa.Integer(), True, None),
        ('next_change_date', sa.Date(), True, None),
        ('date_warning_notified', sa.Boolean(), False, sa.text('0')),
        ('date_overdue_notified', sa.Boolean(), False, sa.text('0')),
    ]
    for col_name, col_type, nullable, server_default in replacements_cols:
        if col_name not in rep_columns:
            op.add_column('replacements', sa.Column(col_name, type_=col_type, nullable=nullable, server_default=server_default))


def downgrade() -> None:
    conn = op.get_bind()
    veh_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
    rep_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(replacements)")).fetchall()]

    for col_name in [
        'oil_interval_months', 'transmission_interval_months',
        'brake_interval_months', 'coolant_interval_months',
        'power_steering_interval_months', 'differential_oil_interval_months',
        'tire_notify_enabled',
    ]:
        if col_name in veh_columns:
            op.drop_column('vehicles', col_name)

    for col_name in ['interval_months', 'next_change_date', 'date_warning_notified', 'date_overdue_notified']:
        if col_name in rep_columns:
            op.drop_column('replacements', col_name)
