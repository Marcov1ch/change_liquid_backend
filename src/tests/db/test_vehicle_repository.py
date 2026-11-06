from unittest.mock import MagicMock

from app.db.models import VehicleDB
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import VehicleDTO


def _vehicle_db() -> VehicleDB:
    return VehicleDB(
        brand_id=1,
        model_id=1,
        plate_number='А123АА178',
        year=2020,
        current_km=10000,
        owner_id=1,
        parking_monthly_notify_enabled=False,
    )


def _vehicle_dto() -> VehicleDTO:
    return VehicleDTO(
        id=1,
        brand='VW',
        model='Golf',
        brand_id=1,
        model_id=1,
        plate_number='А123АА178',
        year=2020,
        current_km=10000,
        is_active=True,
        owner_id=1,
        intervals={},
        notify_flags={'parking_monthly': False},
    )


def test_intervals_and_flags_reads_parking_notify_flag() -> None:
    _, notify_flags, _ = VehicleRepository._intervals_and_flags(_vehicle_db())

    assert notify_flags['parking_monthly'] is False


def test_apply_intervals_writes_parking_notify_flag() -> None:
    db_vehicle = _vehicle_db()
    db_vehicle.parking_monthly_notify_enabled = True

    VehicleRepository(MagicMock())._apply_intervals(db_vehicle, _vehicle_dto())

    assert db_vehicle.parking_monthly_notify_enabled is False
