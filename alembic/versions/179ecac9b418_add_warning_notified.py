"""add_warning_notified

Revision ID: 179ecac9b418
Revises: 00ec8da4b159
Create Date: 2026-07-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '179ecac9b418'
down_revision: Union[str, Sequence[str], None] = '00ec8da4b159'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    rep_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(replacements)")).fetchall()]

    if 'warning_notified' not in rep_columns:
        op.add_column('replacements', sa.Column('warning_notified', sa.Boolean(), server_default=sa.text('0')))


def downgrade() -> None:
    conn = op.get_bind()
    rep_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(replacements)")).fetchall()]
    if 'warning_notified' in rep_columns:
        op.drop_column('replacements', 'warning_notified')
