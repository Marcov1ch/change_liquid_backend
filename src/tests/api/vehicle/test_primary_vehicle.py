import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.vehicle.handler import VehicleHandler
from app.db.models import Base, UserDB, VehicleDB
from app.services.dto import VehicleDTO


def _user() -> UserDB:
    return UserDB(
        username='owner',
        email='owner@example.com',
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


def _dto(vehicle: VehicleDB) -> VehicleDTO:
    return VehicleDTO(
        id=vehicle.id,
        brand='VW',
        model='Golf',
        brand_id=1,
        model_id=1,
        plate_number=vehicle.plate_number,
        year=2020,
        current_km=10000,
        is_active=True,
        owner_id=vehicle.owner_id,
    )


def test_archive_primary_promotes_next_active() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user = _user()
        db.add(user)
        db.commit()
        first = _vehicle(user.id, 'A123AA178')
        second = _vehicle(user.id, 'B456BB178')
        db.add_all([first, second])
        db.commit()
        user.primary_vehicle_id = first.id
        db.commit()
        second_id = second.id

        asyncio.run(VehicleHandler().delete_vehicle(db=db, vehicle=_dto(first)))
        db.refresh(user)

    assert user.primary_vehicle_id == second_id


def test_archive_non_primary_keeps_primary() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        user = _user()
        db.add(user)
        db.commit()
        first = _vehicle(user.id, 'A123AA178')
        second = _vehicle(user.id, 'B456BB178')
        db.add_all([first, second])
        db.commit()
        user.primary_vehicle_id = second.id
        db.commit()
        second_id = second.id

        asyncio.run(VehicleHandler().delete_vehicle(db=db, vehicle=_dto(first)))
        db.refresh(user)

    assert user.primary_vehicle_id == second_id
