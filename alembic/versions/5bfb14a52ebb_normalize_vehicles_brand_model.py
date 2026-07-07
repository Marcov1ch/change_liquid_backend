"""normalize_vehicles_brand_model

Revision ID: 5bfb14a52ebb
Revises: 53017120261f
Create Date: 2026-07-07 16:28:27.116092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5bfb14a52ebb'
down_revision: Union[str, Sequence[str], None] = '53017120261f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Шаг 1: добавляем model_id как nullable (для backfill)
    columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
    if 'model_id' not in columns:
        op.add_column('vehicles', sa.Column('model_id', sa.Integer(), nullable=True))

    # Шаг 2: backfill brand_id для записей где он NULL
    conn.execute(
        sa.text("""
            UPDATE vehicles
            SET brand_id = (SELECT id FROM brands WHERE brands.name = vehicles.brand)
            WHERE brand_id IS NULL
        """)
    )

    # Шаг 3: backfill model_id по названию модели + brand_id
    conn.execute(
        sa.text("""
            UPDATE vehicles
            SET model_id = (
                SELECT models.id FROM models
                JOIN brands ON models.brand_id = brands.id
                WHERE brands.id = vehicles.brand_id
                  AND models.name = vehicles.model
            )
            WHERE model_id IS NULL
        """)
    )

    # Шаг 4: batch-миграция — делаем NOT NULL, дропаем brand/model, добавляем FK
    with op.batch_alter_table('vehicles') as batch_op:
        batch_op.alter_column('brand_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column('model_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column('owner_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.create_foreign_key('fk_vehicles_brand_id', 'brands', ['brand_id'], ['id'])
        batch_op.create_foreign_key('fk_vehicles_model_id', 'models', ['model_id'], ['id'])
        batch_op.create_foreign_key('fk_vehicles_owner_id', 'users', ['owner_id'], ['id'])
        batch_op.drop_column('brand')
        batch_op.drop_column('model')


def downgrade() -> None:
    conn = op.get_bind()

    with op.batch_alter_table('vehicles') as batch_op:
        batch_op.add_column(sa.Column('brand', sa.VARCHAR(), nullable=True))
        batch_op.add_column(sa.Column('model', sa.VARCHAR(), nullable=True))

    # Восстанавливаем brand/model из brands/models таблиц
    conn.execute(
        sa.text("""
            UPDATE vehicles
            SET brand = (SELECT name FROM brands WHERE brands.id = vehicles.brand_id),
                model = (SELECT name FROM models WHERE models.id = vehicles.model_id)
        """)
    )

    with op.batch_alter_table('vehicles') as batch_op:
        batch_op.alter_column('brand', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('model', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.drop_constraint('fk_vehicles_brand_id', type_='foreignkey')
        batch_op.drop_constraint('fk_vehicles_model_id', type_='foreignkey')
        batch_op.drop_constraint('fk_vehicles_owner_id', type_='foreignkey')
        batch_op.alter_column('brand_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.alter_column('model_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.alter_column('owner_id', existing_type=sa.INTEGER(), nullable=True)
