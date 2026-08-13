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


def test_reset_date_notify_flags_delegates_to_repository() -> None:
    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.reset_date_notify_flags.return_value = 3

    result = service.reset_date_notify_flags(1)
    service.repository.reset_date_notify_flags.assert_called_once_with(1)
    assert result == 3
