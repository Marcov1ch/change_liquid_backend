"""add_insurance_notify

Revision ID: b8c9d0e1f2a3
Revises: f6b7c8d9e0f1
Create Date: 2026-11-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'f6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
    if 'insurance_notify_enabled' not in columns:
        op.add_column(
            'vehicles',
            sa.Column('insurance_notify_enabled', sa.Boolean(), server_default=sa.text('1')),
        )


def downgrade() -> None:
    conn = op.get_bind()

    columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
    if 'insurance_notify_enabled' in columns:
        op.drop_column('vehicles', 'insurance_notify_enabled')
