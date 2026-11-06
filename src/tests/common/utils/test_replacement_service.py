from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.common.enums import ComponentType
from app.services.dto import ReplacementDTO, VehicleDTO
from app.services.replacement_service import ReplacementService


@pytest.fixture
def vehicle_dto() -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='', model='', brand_id=1, model_id=1,
        plate_number='', year=2000, current_km=10000,
        is_active=True, owner_id=1,
        intervals={'engine_oil': 7000},
        notify_flags={},
    )


@patch.object(ReplacementService, '_validate_common')
@patch.object(ReplacementService, '_validate_sequence')
@patch.object(ReplacementService, '_update_vehicle_km_if_needed')
def test_raises_on_duplicate(
    mock_update_km: MagicMock,
    mock_sequence: MagicMock,
    mock_common: MagicMock,
    vehicle_dto: VehicleDTO,
) -> None:
    request = MagicMock()
    request.component_type = ComponentType.ENGINE_OIL
    request.km_at_replacement = 10000
    request.component_name = 'Mobil 1'
    request.replacement_date = date(2024, 1, 1)
    request.component_price = 0
    request.work_price = 0
    request.next_change_date = None

    existing = ReplacementDTO(
        id=1, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=0,
        work_price=0,
        replacement_date=date(2024, 1, 1),
        km_at_replacement=10000,
        interval_km=7000,
    )

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.find_by_vehicle_component_and_km.return_value = existing

    with pytest.raises(ValueError, match='уже существует'):
        service.create(1, request, vehicle_dto)


@patch.object(ReplacementService, '_validate_common')
@patch.object(ReplacementService, '_validate_sequence')
@patch.object(ReplacementService, '_update_vehicle_km_if_needed')
def test_no_error_on_different_km(
    mock_update_km: MagicMock,
    mock_sequence: MagicMock,
    mock_common: MagicMock,
    vehicle_dto: VehicleDTO,
) -> None:
    request = MagicMock()
    request.component_type = ComponentType.ENGINE_OIL
    request.km_at_replacement = 15000
    request.component_name = 'Mobil 1'
    request.replacement_date = date(2024, 6, 1)
    request.component_price = 0
    request.work_price = 0
    request.interval_km = 7000
    request.next_change_date = None

    existing = ReplacementDTO(
        id=1, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=0,
        work_price=0,
        replacement_date=date(2024, 1, 1),
        km_at_replacement=10000,
        interval_km=7000,
    )

    def _find_by_km(
        vehicle_id: int,
        component_type: ComponentType,
        km: int,
    ) -> ReplacementDTO | None:
        if km == 10000:
            return existing
        return None

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.find_by_vehicle_component_and_km.side_effect = _find_by_km
    service.vehicle_repository = MagicMock()
    saved = ReplacementDTO(
        id=2, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=0,
        work_price=0,
        replacement_date=date(2024, 6, 1),
        km_at_replacement=15000,
        interval_km=7000,
    )
    service.repository.save.return_value = saved

    result = service.create(1, request, vehicle_dto)
    assert result is not None
    assert result.km_at_replacement == 15000


@patch.object(ReplacementService, '_validate_common')
@patch.object(ReplacementService, '_validate_sequence')
@patch.object(ReplacementService, '_update_vehicle_km_if_needed')
def test_create_computes_next_change_date_from_vehicle_months(
    mock_update_km: MagicMock,
    mock_sequence: MagicMock,
    mock_common: MagicMock,
) -> None:
    vehicle = VehicleDTO(
        id=1, brand='', model='', brand_id=1, model_id=1,
        plate_number='', year=2000, current_km=10000,
        is_active=True, owner_id=1,
        intervals={'engine_oil': 7000},
        notify_flags={},
        interval_months={'engine_oil': 12},
    )

    request = MagicMock()
    request.component_type = ComponentType.ENGINE_OIL
    request.km_at_replacement = 15000
    request.component_name = 'Mobil 1'
    request.replacement_date = date(2026, 1, 15)
    request.component_price = 0
    request.work_price = 0
    request.next_change_date = None

    saved = ReplacementDTO(
        id=2, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=0,
        work_price=0,
        replacement_date=date(2026, 1, 15),
        km_at_replacement=15000,
        interval_km=7000,
        interval_months=12,
        next_change_date=date(2027, 1, 15),
    )

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.find_by_vehicle_component_and_km.return_value = None
    service.vehicle_repository = MagicMock()
    service.repository.save.return_value = saved

    result = service.create(1, request, vehicle, commit=False)
    assert result is not None
    assert result.next_change_date == date(2027, 1, 15)
    assert result.interval_months == 12


def test_create_insurance_requires_next_change_date(vehicle_dto: VehicleDTO) -> None:
    request = MagicMock()
    request.component_type = ComponentType.INSURANCE
    request.next_change_date = None

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.vehicle_repository = MagicMock()

    with pytest.raises(ValueError, match='дату окончания'):
        service.create(1, request, vehicle_dto)

    service.repository.save.assert_not_called()


def test_create_insurance_stores_zero_km_and_no_work_price(vehicle_dto: VehicleDTO) -> None:
    request = MagicMock()
    request.component_type = ComponentType.INSURANCE
    request.km_at_replacement = 999
    request.component_name = 'ОСАГО'
    request.replacement_date = date(2026, 1, 15)
    request.component_price = 12000
    request.work_price = 500
    request.next_change_date = date(2027, 1, 15)

    saved = ReplacementDTO(
        id=2, vehicle_id=1,
        component_type=ComponentType.INSURANCE,
        component_name='ОСАГО',
        component_price=12000,
        work_price=None,
        replacement_date=date(2026, 1, 15),
        km_at_replacement=0,
        interval_km=0,
        next_change_date=date(2027, 1, 15),
    )

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.save.return_value = saved
    service.vehicle_repository = MagicMock()

    result = service.create(1, request, vehicle_dto, commit=False)

    assert result is saved
    created = service.repository.save.call_args.args[0]
    assert created.km_at_replacement == 0
    assert created.interval_km == 0
    assert created.interval_months is None
    assert created.work_price is None
    assert created.next_change_date == date(2027, 1, 15)
    service.repository.find_by_vehicle_component_and_km.assert_not_called()


def test_get_tire_km_traveled_counts_between_records() -> None:
    first = ReplacementDTO(
        id=1, vehicle_id=1,
        component_type=ComponentType.TIRE_CHANGE,
        component_name='Зимние',
        component_price=0,
        work_price=0,
        replacement_date=date(2024, 1, 1),
        km_at_replacement=10000,
        interval_km=0,
    )
    second = ReplacementDTO(
        id=2, vehicle_id=1,
        component_type=ComponentType.TIRE_CHANGE,
        component_name='Летние',
        component_price=0,
        work_price=0,
        replacement_date=date(2024, 6, 1),
        km_at_replacement=15000,
        interval_km=0,
    )

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.find_by_vehicle_and_component.return_value = [second, first]

    result = service.get_tire_km_traveled(1, 18000)

    assert result == {1: 5000, 2: 3000}


def test_reset_date_notify_flags_delegates_to_repository() -> None:
    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.reset_date_notify_flags.return_value = 3

    result = service.reset_date_notify_flags(1)
    service.repository.reset_date_notify_flags.assert_called_once_with(1)
    assert result == 3


def test_create_parking_requires_next_change_date(vehicle_dto: VehicleDTO) -> None:
    request = MagicMock()
    request.component_type = ComponentType.PARKING_MONTHLY
    request.next_change_date = None

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.vehicle_repository = MagicMock()

    with pytest.raises(ValueError, match='дату окончания'):
        service.create(1, request, vehicle_dto)

    service.repository.save.assert_not_called()


def test_create_parking_rejects_end_before_start(vehicle_dto: VehicleDTO) -> None:
    request = MagicMock()
    request.component_type = ComponentType.PARKING_MONTHLY
    request.replacement_date = date(2026, 2, 1)
    request.next_change_date = date(2026, 1, 31)

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.vehicle_repository = MagicMock()

    with pytest.raises(ValueError, match='не может быть раньше'):
        service.create(1, request, vehicle_dto)

    service.repository.save.assert_not_called()


def test_create_parking_stores_zero_km_and_no_work_price(vehicle_dto: VehicleDTO) -> None:
    request = MagicMock()
    request.component_type = ComponentType.PARKING_MONTHLY
    request.km_at_replacement = 999
    request.component_name = 'Машиноместо № 12'
    request.replacement_date = date(2026, 1, 15)
    request.component_price = 8000
    request.work_price = 500
    request.next_change_date = date(2026, 2, 15)

    saved = ReplacementDTO(
        id=2, vehicle_id=1,
        component_type=ComponentType.PARKING_MONTHLY,
        component_name='Машиноместо № 12',
        component_price=8000,
        work_price=None,
        replacement_date=date(2026, 1, 15),
        km_at_replacement=0,
        interval_km=0,
        next_change_date=date(2026, 2, 15),
    )

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.save.return_value = saved
    service.vehicle_repository = MagicMock()

    result = service.create(1, request, vehicle_dto, commit=False)

    assert result is saved
    created = service.repository.save.call_args.args[0]
    assert created.km_at_replacement == 0
    assert created.interval_km == 0
    assert created.interval_months is None
    assert created.work_price is None
    assert created.next_change_date == date(2026, 2, 15)
    service.repository.find_by_vehicle_component_and_km.assert_not_called()


def test_update_parking_ignores_km_and_work_price(vehicle_dto: VehicleDTO) -> None:
    replacement = ReplacementDTO(
        id=2, vehicle_id=1,
        component_type=ComponentType.PARKING_MONTHLY,
        component_name='Машиноместо № 12',
        component_price=8000,
        work_price=None,
        replacement_date=date(2026, 1, 15),
        km_at_replacement=0,
        interval_km=0,
        next_change_date=date(2026, 2, 15),
    )

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.find_by_id.return_value = replacement
    service.repository.save.return_value = replacement
    service.vehicle_repository = MagicMock()
    service.vehicle_repository.find_active_by_id.return_value = vehicle_dto

    service.update(
        2,
        km_at_replacement=999,
        work_price=500,
        component_name='Новое место',
    )

    assert replacement.km_at_replacement == 0
    assert replacement.work_price is None
    assert replacement.component_name == 'Новое место'


def test_update_parking_resets_date_flags_when_next_date_changes(vehicle_dto: VehicleDTO) -> None:
    replacement = ReplacementDTO(
        id=2, vehicle_id=1,
        component_type=ComponentType.PARKING_MONTHLY,
        component_name='Машиноместо № 12',
        component_price=8000,
        work_price=None,
        replacement_date=date(2026, 1, 15),
        km_at_replacement=0,
        interval_km=0,
        next_change_date=date(2026, 2, 15),
    )

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.find_by_id.return_value = replacement
    service.repository.save.return_value = replacement
    service.vehicle_repository = MagicMock()
    service.vehicle_repository.find_active_by_id.return_value = vehicle_dto

    service.update(2, next_change_date=date(2026, 3, 15))

    service.repository.update_date_notify_tracking.assert_called_once_with(
        2,
        date_warning_notified=False,
        date_overdue_notified=False,
    )
