"""add_vehicle_reference

Revision ID: b3c4d5e6f7a8
Revises: f7a8b9c0d1e2
Create Date: 2026-11-16 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'vehicle_reference_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('component_type', sa.String(), nullable=False),
        sa.Column('volume_liters', sa.Numeric(6, 2), nullable=True),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('vehicle_id', 'component_type', name='uq_vehicle_reference_component'),
    )
    op.create_index(
        'ix_vehicle_reference_items_vehicle_id',
        'vehicle_reference_items',
        ['vehicle_id'],
    )

    op.create_table(
        'vehicle_reference_variants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('reference_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('approvals', sa.String(300), nullable=True),
        sa.ForeignKeyConstraint(
            ['reference_id'],
            ['vehicle_reference_items.id'],
            ondelete='CASCADE',
        ),
    )
    op.create_index(
        'ix_vehicle_reference_variants_reference_id',
        'vehicle_reference_variants',
        ['reference_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_vehicle_reference_variants_reference_id',
        table_name='vehicle_reference_variants',
    )
    op.drop_table('vehicle_reference_variants')
    op.drop_index(
        'ix_vehicle_reference_items_vehicle_id',
        table_name='vehicle_reference_items',
    )
    op.drop_table('vehicle_reference_items')
