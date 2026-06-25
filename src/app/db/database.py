from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base
from app.db.seed import seed_brands


DB_PATH = "/data/app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Создание таблиц и сидирование справочников."""
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        seed_brands(session)


def get_db() -> Session:  # type: ignore
    """Получение сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
