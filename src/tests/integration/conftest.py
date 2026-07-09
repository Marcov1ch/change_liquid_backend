import os
import tempfile
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.database import get_db
from app.db.seed import seed_brands
from app.auth.handler import router as auth_router
from app.api.routes import setup_routes
from app.auth.jwt import create_access_token
from app.auth.password import hash_password
from app.db.models import UserDB


@pytest.fixture
def db_engine():
    _, db_path = tempfile.mkstemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    seed_brands(session)
    session.close()
    yield engine
    engine.dispose()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_engine):
    def override_get_db():
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI(title="Change Liquid Test")
    app.include_router(auth_router)
    setup_routes(app)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    user = UserDB(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    user = UserDB(
        username="otheruser",
        email="other@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token(data={"sub": other_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def default_vehicle_data():
    return {
        "brand": "Toyota",
        "model": "Camry",
        "plate_number": "А123АА178",
        "year": 2020,
        "current_km": 50000,
        "oil_interval_km": 7000,
        "transmission_interval_km": 60000,
        "brake_interval_km": 40000,
        "coolant_interval_km": 60000,
        "power_steering_interval_km": 40000,
        "differential_oil_interval_km": 80000,
    }
