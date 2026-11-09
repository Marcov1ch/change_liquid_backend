import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status

from app.api.fuel_record.handler import FuelRecordHandler
from app.api.fuel_record.schema import (
    FuelRecordCreateRequest,
    FuelRecordResponse,
    FuelRecordUpdateRequest,
)
from app.services.dto import FuelRecordDTO, VehicleDTO


def _vehicle() -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='VW', model='Golf', brand_id=1, model_id=1,
        plate_number='А123АА178', year=2015, current_km=20000,
        is_active=True, owner_id=1,
    )


def _record(record_id: int = 1) -> FuelRecordDTO:
    return FuelRecordDTO(
        id=record_id,
        vehicle_id=1,
        fuel_date=date(2026, 1, 15),
        km_at_fuel=15000,
        liters=35.5,
        total_cost=2500,
        consumption_l_per_100km=7.1,
    )


def _create_request() -> FuelRecordCreateRequest:
    return FuelRecordCreateRequest(
        fuel_date=date(2026, 1, 15),
        km_at_fuel=15000,
        liters=35.5,
        total_cost=2500,
    )


def test_create_fuel_record_returns_response() -> None:
    db = MagicMock()
    request = _create_request()
    with patch('app.api.fuel_record.handler.FuelRecordService') as service_cls:
        service_cls.return_value.create.return_value = _record()

        response = asyncio.run(
            FuelRecordHandler().create_fuel_record(
                request=request,
                db=db,
                vehicle=_vehicle(),
            )
        )

    assert isinstance(response, FuelRecordResponse)
    assert response.id == 1
    assert response.liters == 35.5
    assert response.consumption_l_per_100km == 7.1
    service_cls.return_value.create.assert_called_once_with(1, request, _vehicle())


def test_create_fuel_record_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.fuel_record.handler.FuelRecordService') as service_cls:
        service_cls.return_value.create.side_effect = ValueError('Некорректная заправка')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                FuelRecordHandler().create_fuel_record(
                    request=_create_request(),
                    db=db,
                    vehicle=_vehicle(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Некорректная заправка'
    db.rollback.assert_called_once()


def test_get_vehicle_fuel_records_returns_responses() -> None:
    db = MagicMock()
    with patch('app.api.fuel_record.handler.FuelRecordService') as service_cls:
        service_cls.return_value.get_by_vehicle.return_value = [_record(1), _record(2)]

        responses = asyncio.run(
            FuelRecordHandler().get_vehicle_fuel_records(
                db=db,
                vehicle=_vehicle(),
            )
        )

    assert [item.id for item in responses] == [1, 2]
    service_cls.return_value.get_by_vehicle.assert_called_once_with(1)


def test_get_fuel_record_returns_response() -> None:
    response = asyncio.run(FuelRecordHandler().get_fuel_record(record=_record()))

    assert isinstance(response, FuelRecordResponse)
    assert response.id == 1
    assert response.fuel_date == date(2026, 1, 15)
    assert response.km_at_fuel == 15000


def test_update_fuel_record_passes_only_provided_fields() -> None:
    db = MagicMock()
    updated = _record()
    updated.liters = 40.5
    with patch('app.api.fuel_record.handler.FuelRecordService') as service_cls:
        service_cls.return_value.update.return_value = updated

        response = asyncio.run(
            FuelRecordHandler().update_fuel_record(
                request=FuelRecordUpdateRequest(liters=40.5),
                db=db,
                record=_record(),
            )
        )

    assert response.liters == 40.5
    service_cls.return_value.update.assert_called_once_with(1, liters=40.5)


def test_update_fuel_record_returns_404_when_disappeared() -> None:
    db = MagicMock()
    with patch('app.api.fuel_record.handler.FuelRecordService') as service_cls:
        service_cls.return_value.update.return_value = None

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                FuelRecordHandler().update_fuel_record(
                    request=FuelRecordUpdateRequest(liters=40.5),
                    db=db,
                    record=_record(),
                )
            )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == 'Заправка не найдена'


def test_update_fuel_record_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.fuel_record.handler.FuelRecordService') as service_cls:
        service_cls.return_value.update.side_effect = ValueError('Некорректная заправка')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                FuelRecordHandler().update_fuel_record(
                    request=FuelRecordUpdateRequest(liters=40.5),
                    db=db,
                    record=_record(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Некорректная заправка'
    db.rollback.assert_called_once()


def test_delete_fuel_record_returns_message() -> None:
    db = MagicMock()
    with patch('app.api.fuel_record.handler.FuelRecordService') as service_cls:
        response = asyncio.run(
            FuelRecordHandler().delete_fuel_record(db=db, record=_record())
        )

    assert response == {'status': 'ok', 'message': 'Заправка 1 удалена'}
    service_cls.return_value.delete.assert_called_once_with(1)
