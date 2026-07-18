from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.common.enums import ComponentType
from app.common.models.replacement import Replacement
from app.services.dto import VehicleDTO
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

    existing = Replacement(
        id=1, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=0, work_price=0,
        replacement_date=date(2024, 1, 1),
        km_at_replacement=10000, interval_km=7000,
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

    existing = Replacement(
        id=1, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=0, work_price=0,
        replacement_date=date(2024, 1, 1),
        km_at_replacement=10000, interval_km=7000,
    )

    def _find_by_km(
        vehicle_id: int, component_type: ComponentType, km: int,
    ) -> Replacement | None:
        if km == 10000:
            return existing
        return None

    service = ReplacementService.__new__(ReplacementService)
    service.repository = MagicMock()
    service.repository.find_by_vehicle_component_and_km.side_effect = _find_by_km
    service.vehicle_repository = MagicMock()
    saved = Replacement(
        id=2, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=0, work_price=0,
        replacement_date=date(2024, 6, 1),
        km_at_replacement=15000, interval_km=7000,
    )
    service.repository.save.return_value = saved

    result = service.create(1, request, vehicle_dto)
    assert result is not None
    assert result.km_at_replacement == 15000
