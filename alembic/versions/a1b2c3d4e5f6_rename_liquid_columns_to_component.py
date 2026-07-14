"""rename liquid columns to component

Revision ID: a1b2c3d4e5f6
Revises: 179ecac9b418
Create Date: 2026-07-14 13:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '179ecac9b418'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('replacements') as batch_op:
        batch_op.alter_column('liquid_type', new_column_name='component_type')
        batch_op.alter_column('liquid_name', new_column_name='component_name')
        batch_op.alter_column('liquid_price', new_column_name='component_price')


def downgrade() -> None:
    with op.batch_alter_table('replacements') as batch_op:
        batch_op.alter_column('component_type', new_column_name='liquid_type')
        batch_op.alter_column('component_name', new_column_name='liquid_name')
        batch_op.alter_column('component_price', new_column_name='liquid_price')
