"""add_fuel_records

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-11-08 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6c7d8e9f0a1'
down_revision: Union[str, Sequence[str], None] = 'a5b6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fuel_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'vehicle_id',
            sa.Integer(),
            sa.ForeignKey('vehicles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('fuel_date', sa.Date(), nullable=False),
        sa.Column('km_at_fuel', sa.Integer(), nullable=False),
        sa.Column('liters', sa.Float(), nullable=False),
        sa.Column('total_cost', sa.Integer(), nullable=False),
    )
    op.create_index('ix_fuel_records_vehicle_id', 'fuel_records', ['vehicle_id'])
    op.create_index('ix_fuel_records_fuel_date', 'fuel_records', ['fuel_date'])


def downgrade() -> None:
    op.drop_index('ix_fuel_records_fuel_date', table_name='fuel_records')
    op.drop_index('ix_fuel_records_vehicle_id', table_name='fuel_records')
    op.drop_table('fuel_records')
