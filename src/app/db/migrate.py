from alembic.config import Config
from alembic import command
import sqlalchemy as sa
from sqlalchemy import create_engine
from pathlib import Path

from app.db.database import DB_PATH
from app.db.models import Base

_ALEMBIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent / "alembic")


def _create_config() -> Config:
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", _ALEMBIC_DIR)
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH}")
    return alembic_cfg


def run_migrations() -> None:
    """Накатить неприменённые миграции.

    Пустая БД: схема создаётся из моделей один раз и помечается как head,
    чтобы историческая цепочка миграций не пыталась изменять несуществующие таблицы.
    Существующая БД: применяются только новые миграции (инкрементально,
    данные не перезаписываются).
    """
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    alembic_cfg = _create_config()

    with engine.connect() as conn:
        if not sa.inspect(conn).get_table_names():
            Base.metadata.create_all(bind=engine)
            command.stamp(alembic_cfg, "head")
            return

    command.upgrade(alembic_cfg, "head")
