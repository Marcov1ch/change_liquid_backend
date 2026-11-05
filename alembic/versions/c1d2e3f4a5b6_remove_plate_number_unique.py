"""remove plate_number unique

Revision ID: c1d2e3f4a5b6
Revises: b8c9d0e1f2a3
Create Date: 2026-11-05 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _plate_unique_constraints(table: sa.Table) -> list[sa.UniqueConstraint]:
    return [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
        and {column.name for column in constraint.columns} == {'plate_number'}
    ]


def upgrade() -> None:
    conn = op.get_bind()
    metadata = sa.MetaData()
    vehicles = sa.Table('vehicles', metadata, autoload_with=conn)

    plate_uniques = _plate_unique_constraints(vehicles)
    if not plate_uniques:
        return

    for constraint in plate_uniques:
        vehicles.constraints.discard(constraint)

    with op.batch_alter_table('vehicles', copy_from=vehicles, recreate='always'):
        pass


def downgrade() -> None:
    conn = op.get_bind()
    duplicate = conn.execute(
        sa.text(
            'SELECT plate_number FROM vehicles '
            'GROUP BY plate_number HAVING COUNT(*) > 1 LIMIT 1'
        )
    ).first()
    if duplicate:
        raise RuntimeError(
            'Cannot restore unique plate_number: duplicate plates exist in vehicles'
        )

    with op.batch_alter_table('vehicles', recreate='always') as batch_op:
        batch_op.create_unique_constraint(
            'uq_vehicles_plate_number',
            ['plate_number'],
        )
