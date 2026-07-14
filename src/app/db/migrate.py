from alembic.config import Config
from alembic import command
from app.db.database import DB_PATH


def run_migrations() -> None:
    """Автоматически накатить неприменённые миграции."""
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", "alembic")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH}")
    command.upgrade(alembic_cfg, "head")
