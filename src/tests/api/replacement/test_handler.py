from datetime import date, timedelta

from app.api.replacement.handler import ReplacementHandler
from app.common.enums import ComponentType, StatusEnum
from app.services.dto import ReplacementDTO, VehicleDTO


def _vehicle(interval_months: dict | None = None) -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='VW', model='Golf', brand_id=1, model_id=1,
        plate_number='А123АА178', year=2015, current_km=20000,
        is_active=True, owner_id=1,
        intervals={'engine_oil': 7000},
        notify_flags={},
        interval_months=interval_months or {},
    )


def _replacement(component_type: ComponentType = ComponentType.ENGINE_OIL) -> ReplacementDTO:
    return ReplacementDTO(
        id=1, vehicle_id=1,
        component_type=component_type,
        component_name='Mobil 1',
        component_price=0,
        work_price=0,
        replacement_date=date(2026, 1, 15),
        km_at_replacement=15000,
        interval_km=7000,
    )


def test_latest_non_tire_uses_live_vehicle_months() -> None:
    vehicle = _vehicle({'engine_oil': 13})
    response = ReplacementHandler()._to_response(_replacement(), vehicle, is_latest=True)
    assert response.next_change_date == date(2027, 2, 15)
    assert response.days_remaining is not None
    assert response.next_replacement_km == 22000
    assert response.status == StatusEnum.GOOD


def test_latest_non_tire_without_months_has_no_date() -> None:
    vehicle = _vehicle({})
    response = ReplacementHandler()._to_response(_replacement(), vehicle, is_latest=True)
    assert response.next_change_date is None
    assert response.days_remaining is None


def test_archival_non_tire_has_no_next_info() -> None:
    vehicle = _vehicle({'engine_oil': 13})
    response = ReplacementHandler()._to_response(_replacement(), vehicle, is_latest=False)
    assert response.next_change_date is None
    assert response.days_remaining is None
    assert response.next_replacement_km is None
    assert response.km_remaining is None
    assert response.status == StatusEnum.REPLACED


def test_archival_tire_keeps_stored_date() -> None:
    vehicle = _vehicle({})
    replacement = _replacement(ComponentType.TIRE_CHANGE)
    replacement.next_change_date = date(2026, 11, 1)
    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=False)
    assert response.next_change_date == date(2026, 11, 1)
    assert response.next_replacement_km is None


def test_latest_tire_km_traveled_from_current_km() -> None:
    vehicle = _vehicle({})
    replacement = _replacement(ComponentType.TIRE_CHANGE)
    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=True)
    assert response.km_traveled == 5000


def test_tire_km_traveled_uses_passed_value() -> None:
    vehicle = _vehicle({})
    replacement = _replacement(ComponentType.TIRE_CHANGE)
    response = ReplacementHandler()._to_response(
        replacement,
        vehicle,
        is_latest=False,
        km_traveled=2500,
    )
    assert response.km_traveled == 2500


def test_latest_insurance_uses_date_status_and_hides_mileage() -> None:
    vehicle = _vehicle({})
    replacement = _replacement(ComponentType.INSURANCE)
    replacement.km_at_replacement = 0
    replacement.interval_km = 0
    replacement.work_price = None
    replacement.next_change_date = date.today() + timedelta(days=30)

    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=True)

    assert response.status == StatusEnum.GOOD
    assert response.next_change_date == replacement.next_change_date
    assert response.days_remaining == 30
    assert response.next_replacement_km is None
    assert response.km_remaining is None
    assert response.km_traveled is None
    assert response.work_price is None


def test_archival_insurance_keeps_stored_date() -> None:
    vehicle = _vehicle({})
    replacement = _replacement(ComponentType.INSURANCE)
    replacement.km_at_replacement = 0
    replacement.interval_km = 0
    replacement.next_change_date = date(2026, 11, 1)

    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=False)

    assert response.next_change_date == date(2026, 11, 1)
    assert response.status == StatusEnum.REPLACED
    assert response.km_remaining is None
    assert response.km_traveled is None


def test_latest_parking_monthly_uses_date_status_and_hides_mileage() -> None:
    vehicle = _vehicle({})
    replacement = _replacement(ComponentType.PARKING_MONTHLY)
    replacement.km_at_replacement = 0
    replacement.interval_km = 0
    replacement.work_price = None
    replacement.next_change_date = date.today() + timedelta(days=3)

    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=True)

    assert response.status == StatusEnum.GOOD
    assert response.days_remaining == 3
    assert response.next_replacement_km is None
    assert response.km_remaining is None
    assert response.km_traveled is None

    replacement.next_change_date = date.today() + timedelta(days=1)
    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=True)
    assert response.status == StatusEnum.WARNING

    replacement.next_change_date = date.today() - timedelta(days=1)
    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=True)
    assert response.status == StatusEnum.OVERDUE


def test_archival_parking_monthly_keeps_stored_date() -> None:
    vehicle = _vehicle({})
    replacement = _replacement(ComponentType.PARKING_MONTHLY)
    replacement.km_at_replacement = 0
    replacement.interval_km = 0
    replacement.next_change_date = date(2026, 11, 1)

    response = ReplacementHandler()._to_response(replacement, vehicle, is_latest=False)

    assert response.next_change_date == date(2026, 11, 1)
    assert response.status == StatusEnum.REPLACED
    assert response.km_remaining is None
    assert response.km_traveled is None
