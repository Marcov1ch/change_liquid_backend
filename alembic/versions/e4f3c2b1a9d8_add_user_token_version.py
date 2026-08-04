"""add_user_token_version

Revision ID: e4f3c2b1a9d8
Revises: 9a8b7c6d5e4f
Create Date: 2026-08-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e4f3c2b1a9d8'
down_revision: Union[str, Sequence[str], None] = '9a8b7c6d5e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    user_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(users)")).fetchall()]

    if 'token_version' not in user_columns:
        op.add_column(
            'users',
            sa.Column('token_version', sa.Integer(), nullable=False, server_default=sa.text('0')),
        )


def downgrade() -> None:
    conn = op.get_bind()
    user_columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(users)")).fetchall()]
    if 'token_version' in user_columns:
        op.drop_column('users', 'token_version')
