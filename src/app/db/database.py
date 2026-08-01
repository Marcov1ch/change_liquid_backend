import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.seed import seed_brands


DB_PATH = os.getenv("DB_PATH", "data/app.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Сидирование справочников (схема управляется миграциями)."""
    with SessionLocal() as session:
        seed_brands(session)


def get_db() -> Session:  # type: ignore
    """Получение сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
