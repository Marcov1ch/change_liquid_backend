from unittest.mock import MagicMock

import pytest

from app.common.exceptions import VehicleConflictError
from app.services.dto import VehicleDTO
from app.services.vehicle_service import VehicleService


def _vehicle(vehicle_id: int = 1) -> VehicleDTO:
    return VehicleDTO(
        id=vehicle_id,
        brand='VW',
        model='Golf',
        brand_id=1,
        model_id=1,
        plate_number='А123АА178',
        year=2015,
        current_km=20000,
        is_active=True,
        owner_id=1,
        intervals={'engine_oil': 7000},
        notify_flags={'engine_oil': True},
        interval_months={'engine_oil': 12},
    )


def _service() -> VehicleService:
    service = VehicleService(MagicMock())
    service.repository = MagicMock()
    service.enum_repo = MagicMock()
    service.repository.get_max_replacement_km.return_value = 0
    return service


def test_partial_update_applies_only_given_fields() -> None:
    service = _service()
    dto = _vehicle()
    service.repository.save.return_value = dto

    result = service.partial_update(dto, {'year': 2020, 'current_km': 30000})

    assert result is dto
    assert dto.year == 2020
    assert dto.current_km == 30000
    assert dto.brand == 'VW'
    service.repository.save.assert_called_once_with(dto)
    service.repository.find_by_plate_number.assert_not_called()


def test_partial_update_rejects_plate_number_of_another_vehicle() -> None:
    service = _service()
    service.repository.find_by_plate_number.return_value = _vehicle(vehicle_id=2)

    with pytest.raises(VehicleConflictError):
        service.partial_update(_vehicle(), {'plate_number': 'В456ВВ178'})

    service.repository.save.assert_not_called()


def test_partial_update_allows_same_plate_number() -> None:
    service = _service()
    dto = _vehicle()
    service.repository.find_by_plate_number.return_value = dto
    service.repository.save.return_value = dto

    service.partial_update(dto, {'plate_number': 'А123АА178'})

    assert dto.plate_number == 'А123АА178'
    service.repository.save.assert_called_once_with(dto)


def test_partial_update_validates_km_against_replacements() -> None:
    service = _service()
    service.repository.get_max_replacement_km.return_value = 50000

    with pytest.raises(ValueError):
        service.partial_update(_vehicle(), {'current_km': 100})

    service.repository.save.assert_not_called()


def test_partial_update_resolves_brand_and_model() -> None:
    service = _service()
    dto = _vehicle()
    service.repository.save.return_value = dto
    brand = MagicMock()
    brand.id = 10
    model = MagicMock()
    model.id = 20
    model.name = 'Passat'
    service.enum_repo.get_brand_by_name.return_value = brand
    service.enum_repo.get_models_by_brand.return_value = [model]

    service.partial_update(dto, {'brand': 'VW', 'model': 'Passat'})

    assert dto.brand_id == 10
    assert dto.model == 'Passat'
    assert dto.model_id == 20


def test_partial_update_keeps_nested_none_months() -> None:
    service = _service()
    dto = _vehicle()
    service.repository.save.return_value = dto

    service.partial_update(dto, {'interval_months': {'engine_oil': None}})

    assert dto.interval_months == {'engine_oil': None}
