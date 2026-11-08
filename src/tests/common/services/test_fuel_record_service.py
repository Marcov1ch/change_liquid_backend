from datetime import date, timedelta
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.fuel_record.schema import FuelRecordCreateRequest
from app.db.models import Base, BrandDB, ModelDB, VehicleDB
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import VehicleDTO
from app.services.fuel_record_service import FuelRecordService


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def vehicle(db_session: Session) -> VehicleDTO:
    db_session.add(BrandDB(id=1, name='VW'))
    db_session.add(ModelDB(id=1, brand_id=1, name='Golf'))
    db_session.add(VehicleDB(
        id=1,
        brand_id=1,
        model_id=1,
        plate_number='AB-123-CD',
        year=2015,
        current_km=10000,
        is_active=True,
        owner_id=1,
    ))
    db_session.commit()

    dto = VehicleRepository(db_session).find_active_by_id(1)
    assert dto is not None
    return dto


def _request(
    fuel_date: date = date(2026, 5, 10),
    km_at_fuel: int = 10500,
    liters: float = 35.0,
    total_cost: int = 1800,
) -> FuelRecordCreateRequest:
    return FuelRecordCreateRequest.model_construct(
        fuel_date=fuel_date,
        km_at_fuel=km_at_fuel,
        liters=liters,
        total_cost=total_cost,
    )


def test_create_and_calculate_consumption(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    service = FuelRecordService(db_session)
    service.create(vehicle.id, _request(km_at_fuel=10000, liters=40.0), vehicle)
    service.create(vehicle.id, _request(km_at_fuel=10500, liters=35.0), vehicle)
    service.create(vehicle.id, _request(km_at_fuel=11000, liters=30.0), vehicle)

    records = service.get_by_vehicle(vehicle.id)  # type: ignore[arg-type]

    assert [record.km_at_fuel for record in records] == [11000, 10500, 10000]
    assert records[0].consumption_l_per_100km == 6.0
    assert records[1].consumption_l_per_100km == 7.0
    assert records[2].consumption_l_per_100km is None


def test_update_vehicle_km_only_upward(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    service = FuelRecordService(db_session)

    service.create(vehicle.id, _request(km_at_fuel=9000), vehicle)
    assert VehicleRepository(db_session).find_by_id(1).current_km == 10000  # type: ignore[union-attr]

    service.create(vehicle.id, _request(km_at_fuel=12000), vehicle)
    assert VehicleRepository(db_session).find_by_id(1).current_km == 12000  # type: ignore[union-attr]


def test_rejects_future_date(db_session: Session, vehicle: VehicleDTO) -> None:
    service = FuelRecordService(db_session)

    with pytest.raises(ValueError, match='позже сегодняшнего'):
        service.create(
            vehicle.id,
            _request(fuel_date=date.today() + timedelta(days=1)),
            vehicle,
        )


def test_rejects_negative_km(db_session: Session, vehicle: VehicleDTO) -> None:
    service = FuelRecordService(db_session)

    with pytest.raises(ValueError, match='отрицательным'):
        service.create(vehicle.id, _request(km_at_fuel=-1), vehicle)


def test_rejects_non_positive_liters(db_session: Session, vehicle: VehicleDTO) -> None:
    service = FuelRecordService(db_session)

    with pytest.raises(ValueError, match='больше 0'):
        service.create(vehicle.id, _request(liters=0), vehicle)


def test_rejects_negative_cost(db_session: Session, vehicle: VehicleDTO) -> None:
    service = FuelRecordService(db_session)

    with pytest.raises(ValueError, match='отрицательной'):
        service.create(vehicle.id, _request(total_cost=-1), vehicle)


def test_consumption_is_none_for_same_km(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    service = FuelRecordService(db_session)
    service.create(vehicle.id, _request(km_at_fuel=10000), vehicle)
    service.create(vehicle.id, _request(km_at_fuel=10000), vehicle)

    records = service.get_by_vehicle(vehicle.id)  # type: ignore[arg-type]

    assert all(record.consumption_l_per_100km is None for record in records)


def test_consumption_sorted_by_km_regardless_of_input_order(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    service = FuelRecordService(db_session)
    service.create(vehicle.id, _request(km_at_fuel=11000, liters=30.0), vehicle)
    service.create(vehicle.id, _request(km_at_fuel=10000, liters=40.0), vehicle)

    records = service.get_by_vehicle(vehicle.id)  # type: ignore[arg-type]
    by_km = {record.km_at_fuel: record for record in records}

    assert by_km[10000].consumption_l_per_100km is None
    assert by_km[11000].consumption_l_per_100km == 3.0


def test_update_partial_and_recalculate(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    service = FuelRecordService(db_session)
    first = service.create(vehicle.id, _request(km_at_fuel=10000, liters=40.0), vehicle)
    service.create(vehicle.id, _request(km_at_fuel=10500, liters=35.0), vehicle)

    updated = service.update(first.id, km_at_fuel=9500, liters=30.0)  # type: ignore[arg-type]

    assert updated is not None
    assert updated.km_at_fuel == 9500
    assert updated.liters == 30.0

    records = service.get_by_vehicle(vehicle.id)  # type: ignore[arg-type]
    by_km = {record.km_at_fuel: record for record in records}
    assert by_km[9500].consumption_l_per_100km is None
    assert by_km[10500].consumption_l_per_100km == round(35.0 / 1000 * 100, 2)


def test_delete_and_delete_by_vehicle(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    service = FuelRecordService(db_session)
    first = service.create(vehicle.id, _request(km_at_fuel=10000), vehicle)
    service.create(vehicle.id, _request(km_at_fuel=10500), vehicle)

    assert service.delete(first.id) is True  # type: ignore[arg-type]
    assert service.delete(first.id) is False  # type: ignore[arg-type]

    deleted = service.delete_by_vehicle(vehicle.id)  # type: ignore[arg-type]

    assert deleted == 1
    assert service.get_by_vehicle(vehicle.id) == []  # type: ignore[arg-type]
