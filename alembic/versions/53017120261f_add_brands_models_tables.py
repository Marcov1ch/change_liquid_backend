"""add brands_models_tables

Revision ID: 53017120261f
Revises: 
Create Date: 2026-06-25 17:31:25.860888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '53017120261f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BRANDS_MODELS: dict[str, list[str]] = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser", "Highlander", "Prius"],
    "Honda": ["CR-V", "Civic", "Accord", "Pilot", "HR-V", "Fit"],
    "BMW": ["X5", "X3", "3 Series", "5 Series", "7 Series", "X1"],
    "Mercedes": ["C-Class", "E-Class", "S-Class", "GLE", "GLC", "A-Class"],
    "Audi": ["A4", "A6", "Q5", "Q7", "A3", "Q3"],
    "Volkswagen": ["Golf", "Passat", "Tiguan", "Polo", "Touareg"],
    "Ford": ["Focus", "Mondeo", "Kuga", "Fiesta", "Explorer"],
    "Chevrolet": ["Cruze", "Malibu", "Traverse", "Equinox", "Spark"],
    "Hyundai": ["Sonata", "Elantra", "Santa Fe", "Tucson", "Kona"],
    "Kia": ["Optima", "Sportage", "Sorento", "Rio", "Ceed"],
    "Nissan": ["X-Trail", "Qashqai", "Juke", "Teana", "Murano"],
    "Mazda": ["CX-5", "CX-9", "Mazda3", "Mazda6", "CX-30"],
    "Subaru": ["Outback", "Forester", "Impreza", "Legacy", "XV"],
    "Volvo": ["XC60", "XC90", "S60", "V90", "XC40"],
}


def upgrade() -> None:
    conn = op.get_bind()

    # Create brands table if not exists
    if not conn.dialect.has_table(conn, 'brands'):
        op.create_table('brands',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index(op.f('ix_brands_id'), 'brands', ['id'], unique=False)

        # Seed brands
        brands_table = sa.table('brands', sa.column('id', sa.Integer), sa.column('name', sa.String))
        for brand_name in BRANDS_MODELS:
            op.execute(brands_table.insert().values(name=brand_name))

    # Create models table if not exists
    if not conn.dialect.has_table(conn, 'models'):
        op.create_table('models',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('brand_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.ForeignKeyConstraint(['brand_id'], ['brands.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_models_id'), 'models', ['id'], unique=False)

        # Seed models
        brands_table = sa.table('brands', sa.column('id', sa.Integer), sa.column('name', sa.String))
        models_table = sa.table('models', sa.column('id', sa.Integer), sa.column('brand_id', sa.Integer), sa.column('name', sa.String))
        for brand_name, models in BRANDS_MODELS.items():
            brand_subq = sa.select(brands_table.c.id).where(brands_table.c.name == brand_name).scalar_subquery()
            for model_name in models:
                op.execute(models_table.insert().values(brand_id=brand_subq, name=model_name))

    # Add brand_id to vehicles and migrate existing data
    if conn.dialect.has_table(conn, 'vehicles'):
        columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
        if 'brand_id' not in columns:
            op.add_column('vehicles', sa.Column('brand_id', sa.Integer(), nullable=True))

            brands_table = sa.table('brands', sa.column('id', sa.Integer), sa.column('name', sa.String))
            vehicles_table = sa.table('vehicles', sa.column('brand_id', sa.Integer), sa.column('brand', sa.String))

            # Only migrate data if brands table has data
            brand_count = conn.execute(sa.text("SELECT COUNT(*) FROM brands")).scalar()
            if brand_count > 0:
                op.execute(
                    vehicles_table.update().values(
                        brand_id=sa.select(brands_table.c.id)
                        .where(brands_table.c.name == vehicles_table.c.brand)
                        .scalar_subquery()
                    )
                )


def downgrade() -> None:
    conn = op.get_bind()

    if conn.dialect.has_table(conn, 'vehicles'):
        columns = [col.name for col in conn.execute(sa.text("PRAGMA table_info(vehicles)")).fetchall()]
        if 'brand_id' in columns:
            op.drop_column('vehicles', 'brand_id')

    op.drop_table('models')
    op.drop_table('brands')
