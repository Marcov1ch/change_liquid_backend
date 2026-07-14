"""add_notify_fields

Revision ID: 00ec8da4b159
Revises: 5bfb14a52ebb
Create Date: 2026-07-10 10:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '00ec8da4b159'
down_revision: Union[str, Sequence[str], None] = '5bfb14a52ebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- vehicles ---
    columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]

    notify_fields = [
        ('oil_notify_enabled', sa.Boolean(), 1),
        ('transmission_notify_enabled', sa.Boolean(), 1),
        ('brake_notify_enabled', sa.Boolean(), 1),
        ('coolant_notify_enabled', sa.Boolean(), 1),
        ('power_steering_notify_enabled', sa.Boolean(), 1),
        ('differential_oil_notify_enabled', sa.Boolean(), 1),
    ]
    for col_name, col_type, default in notify_fields:
        if col_name not in columns:
            op.add_column('vehicles', sa.Column(col_name, col_type, server_default=sa.text(str(default))))

    # --- replacements ---
    rep_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(replacements)")).fetchall()]

    if 'critical_notified' not in rep_columns:
        op.add_column('replacements', sa.Column('critical_notified', sa.Boolean(), server_default=sa.text('0')))
    if 'overdue_notified_at_km' not in rep_columns:
        op.add_column('replacements', sa.Column('overdue_notified_at_km', sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()

    columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
    for col_name in ('oil_notify_enabled', 'transmission_notify_enabled', 'brake_notify_enabled',
                     'coolant_notify_enabled', 'power_steering_notify_enabled', 'differential_oil_notify_enabled'):
        if col_name in columns:
            op.drop_column('vehicles', col_name)

    rep_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(replacements)")).fetchall()]
    if 'critical_notified' in rep_columns:
        op.drop_column('replacements', 'critical_notified')
    if 'overdue_notified_at_km' in rep_columns:
        op.drop_column('replacements', 'overdue_notified_at_km')
