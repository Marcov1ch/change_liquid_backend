"""add_tire_sets

Revision ID: 1a2b3c4d5e6f
Revises: b6c7d8e9f0a1
Create Date: 2026-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = 'b6c7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tire_sets',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column(
            'vehicle_id',
            sa.Integer(),
            sa.ForeignKey('vehicles.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('season', sa.String(), nullable=False, server_default='all_season'),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('purchase_price', sa.Integer(), nullable=True),
        sa.Column('accumulated_km', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('installed_km', sa.Integer(), nullable=True),
        sa.Column('installed_date', sa.Date(), nullable=True),
        sa.Column('is_installed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    with op.batch_alter_table('replacements') as batch_op:
        batch_op.add_column(sa.Column('tire_set_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('tire_event_type', sa.String(), nullable=True))
        batch_op.create_index('ix_replacements_tire_set_id', ['tire_set_id'])
        batch_op.create_foreign_key(
            'fk_replacements_tire_set_id',
            'tire_sets',
            ['tire_set_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('replacements') as batch_op:
        batch_op.drop_constraint('fk_replacements_tire_set_id', type_='foreignkey')
        batch_op.drop_index('ix_replacements_tire_set_id')
        batch_op.drop_column('tire_event_type')
        batch_op.drop_column('tire_set_id')

    op.drop_table('tire_sets')
