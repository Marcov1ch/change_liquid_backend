"""add_other_expenses

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-11-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'other_expenses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'vehicle_id',
            sa.Integer(),
            sa.ForeignKey('vehicles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
    )
    op.create_index('ix_other_expenses_vehicle_id', 'other_expenses', ['vehicle_id'])
    op.create_index('ix_other_expenses_expense_date', 'other_expenses', ['expense_date'])


def downgrade() -> None:
    op.drop_index('ix_other_expenses_expense_date', table_name='other_expenses')
    op.drop_index('ix_other_expenses_vehicle_id', table_name='other_expenses')
    op.drop_table('other_expenses')
