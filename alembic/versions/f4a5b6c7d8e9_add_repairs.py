"""add_repairs

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-11-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'repairs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'vehicle_id',
            sa.Integer(),
            sa.ForeignKey('vehicles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('repair_date', sa.Date(), nullable=False),
        sa.Column('km_at_repair', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('total_cost', sa.Integer(), nullable=True),
    )
    op.create_index('ix_repairs_vehicle_id', 'repairs', ['vehicle_id'])
    op.create_index('ix_repairs_repair_date', 'repairs', ['repair_date'])

    op.create_table(
        'repair_components',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'repair_id',
            sa.Integer(),
            sa.ForeignKey('repairs.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('component_type', sa.String(), nullable=False),
        sa.UniqueConstraint('repair_id', 'component_type', name='uq_repair_component'),
    )
    op.create_index('ix_repair_components_repair_id', 'repair_components', ['repair_id'])

    with op.batch_alter_table('replacements', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('source_repair_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_replacements_source_repair_id',
            'repairs',
            ['source_repair_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index(
            'ix_replacements_source_repair_id',
            ['source_repair_id'],
        )


def downgrade() -> None:
    op.drop_index('ix_replacements_source_repair_id', table_name='replacements')
    with op.batch_alter_table('replacements', schema=None) as batch_op:
        batch_op.drop_column('source_repair_id')

    op.drop_index('ix_repair_components_repair_id', table_name='repair_components')
    op.drop_table('repair_components')
    op.drop_index('ix_repairs_repair_date', table_name='repairs')
    op.drop_index('ix_repairs_vehicle_id', table_name='repairs')
    op.drop_table('repairs')
