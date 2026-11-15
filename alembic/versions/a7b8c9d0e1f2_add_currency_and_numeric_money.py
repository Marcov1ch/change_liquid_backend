"""add_currency_and_numeric_money

Revision ID: a7b8c9d0e1f2
Revises: 3c4d5e6f7a8b
Create Date: 2026-11-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = '3c4d5e6f7a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MONEY_COLUMNS = {
    'tire_sets': (('purchase_price', True),),
    'replacements': (('component_price', True), ('work_price', True)),
    'other_expenses': (('amount', False),),
    'repairs': (('work_cost', False), ('parts_cost', False)),
    'fuel_records': (('total_cost', False),),
}


def _columns(table: str) -> list[str]:
    conn = op.get_bind()
    rows = conn.execute(sa.text(f'PRAGMA table_info({table})')).fetchall()
    return [row[1] for row in rows]


def upgrade() -> None:
    user_columns = _columns('users')
    if 'currency' not in user_columns:
        op.add_column(
            'users',
            sa.Column('currency', sa.String(length=3), nullable=False, server_default='RUB'),
        )
    if 'profile_visited' not in user_columns:
        op.add_column(
            'users',
            sa.Column(
                'profile_visited',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('0'),
            ),
        )
        op.execute(sa.text('UPDATE users SET profile_visited = 1'))

    for table, columns in _MONEY_COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for column, nullable in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.Integer(),
                    type_=sa.Numeric(12, 2),
                    existing_nullable=nullable,
                    nullable=nullable,
                )


def downgrade() -> None:
    for table, columns in _MONEY_COLUMNS.items():
        with op.batch_alter_table(table) as batch_op:
            for column, nullable in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.Numeric(12, 2),
                    type_=sa.Integer(),
                    existing_nullable=nullable,
                    nullable=nullable,
                )

    user_columns = _columns('users')
    if 'profile_visited' in user_columns:
        op.drop_column('users', 'profile_visited')
    if 'currency' in user_columns:
        op.drop_column('users', 'currency')
