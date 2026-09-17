"""add_vehicle_sizes

Revision ID: 0f1a2b3c4d5e
Revises: e4f3c2b1a9d8
Create Date: 2026-09-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0f1a2b3c4d5e'
down_revision: Union[str, Sequence[str], None] = 'e4f3c2b1a9d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'vehicle_sizes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('diameter', sa.Integer(), nullable=True),
        sa.Column('pcd', sa.String(), nullable=True),
        sa.Column('et_from', sa.Integer(), nullable=True),
        sa.Column('et_to', sa.Integer(), nullable=True),
        sa.Column('width_from', sa.Float(), nullable=True),
        sa.Column('width_to', sa.Float(), nullable=True),
        sa.Column('size', sa.String(), nullable=True),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('vehicle_sizes')
