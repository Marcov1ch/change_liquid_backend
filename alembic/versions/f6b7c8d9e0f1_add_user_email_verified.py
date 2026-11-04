"""add_user_email_verified

Revision ID: f6b7c8d9e0f1
Revises: d4e5f6a7b8c9
Create Date: 2026-11-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6b7c8d9e0f1'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _user_columns() -> list:
    conn = op.get_bind()
    return [col.name for col in conn.execute(sa.text("PRAGMA table_info(users)")).fetchall()]


def upgrade() -> None:
    if 'email_verified' not in _user_columns():
        op.add_column(
            'users',
            sa.Column(
                'email_verified',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('0'),
            ),
        )
        op.execute(sa.text('UPDATE users SET email_verified = 1'))


def downgrade() -> None:
    if 'email_verified' in _user_columns():
        op.drop_column('users', 'email_verified')
