"""add_parking_monthly_notify

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-11-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
    if 'parking_monthly_notify_enabled' not in columns:
        op.add_column(
            'vehicles',
            sa.Column('parking_monthly_notify_enabled', sa.Boolean(), server_default=sa.text('1')),
        )


def downgrade() -> None:
    conn = op.get_bind()

    columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
    if 'parking_monthly_notify_enabled' in columns:
        op.drop_column('vehicles', 'parking_monthly_notify_enabled')
