"""add_repair_costs

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-11-08 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'repairs',
        sa.Column('work_cost', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'repairs',
        sa.Column('parts_cost', sa.Integer(), nullable=False, server_default='0'),
    )
    op.execute(
        'UPDATE repairs SET parts_cost = COALESCE(total_cost, 0)'
    )
    with op.batch_alter_table('repairs', schema=None) as batch_op:
        batch_op.drop_column('total_cost')


def downgrade() -> None:
    op.add_column(
        'repairs',
        sa.Column('total_cost', sa.Integer(), nullable=True),
    )
    op.execute(
        'UPDATE repairs SET total_cost = work_cost + parts_cost'
    )
    with op.batch_alter_table('repairs', schema=None) as batch_op:
        batch_op.drop_column('parts_cost')
        batch_op.drop_column('work_cost')
