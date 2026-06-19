import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base


DB_PATH = os.getenv("DATABASE_PATH", "./app.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Создание таблиц."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:  # type: ignore
    """Получение сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
