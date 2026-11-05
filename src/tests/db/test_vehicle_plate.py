from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.models import Base, VehicleDB


def _vehicle() -> VehicleDB:
    return VehicleDB(
        brand_id=1,
        model_id=1,
        plate_number='А123АА178',
        year=2020,
        current_km=10000,
        owner_id=1,
    )


def test_vehicles_can_have_same_plate_number() -> None:
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all([_vehicle(), _vehicle()])
        session.commit()

        count = session.scalar(select(func.count()).select_from(VehicleDB))

    assert count == 2
