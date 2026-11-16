from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.routes.account import update_primary_vehicle
from app.auth.schemas import UpdatePrimaryVehicleRequest
from app.db.models import Base, UserDB, VehicleDB


def _user(username: str) -> UserDB:
    return UserDB(
        username=username,
        email=f'{username}@example.com',
        hashed_password='x',
        created_at=datetime.now(timezone.utc),
    )


def _vehicle(owner_id: int, plate: str) -> VehicleDB:
    return VehicleDB(
        brand_id=1,
        model_id=1,
        plate_number=plate,
        year=2020,
        current_km=10000,
        owner_id=owner_id,
    )


def test_set_primary_vehicle() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user = _user('owner')
        db.add(user)
        db.commit()
        vehicle = _vehicle(user.id, 'A123AA178')
        db.add(vehicle)
        db.commit()
        vehicle_id = vehicle.id

        response = update_primary_vehicle(
            UpdatePrimaryVehicleRequest(vehicle_id=vehicle.id),
            db=db,
            current_user=user,
        )

    assert response.primary_vehicle_id == vehicle_id


def test_cannot_set_foreign_vehicle() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        owner = _user('owner')
        foreign = _user('foreign')
        db.add_all([owner, foreign])
        db.commit()
        vehicle = _vehicle(foreign.id, 'B456BB178')
        db.add(vehicle)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            update_primary_vehicle(
                UpdatePrimaryVehicleRequest(vehicle_id=vehicle.id),
                db=db,
                current_user=owner,
            )

    assert exc_info.value.status_code == 404
