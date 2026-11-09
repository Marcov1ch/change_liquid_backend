import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status

from app.api.repair.handler import RepairHandler
from app.api.repair.schema import (
    RepairCreateRequest,
    RepairResponse,
    RepairUpdateRequest,
)
from app.common.enums import ComponentType
from app.services.dto import RepairDTO, VehicleDTO


def _vehicle() -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='VW', model='Golf', brand_id=1, model_id=1,
        plate_number='А123АА178', year=2015, current_km=20000,
        is_active=True, owner_id=1,
    )


def _repair(repair_id: int = 1) -> RepairDTO:
    return RepairDTO(
        id=repair_id,
        vehicle_id=1,
        repair_date=date(2026, 1, 15),
        km_at_repair=15000,
        description='Плановое ТО',
        work_cost=2000,
        parts_cost=5000,
        component_types=[ComponentType.ENGINE_OIL],
    )


def _create_request() -> RepairCreateRequest:
    return RepairCreateRequest(
        repair_date=date(2026, 1, 15),
        km_at_repair=15000,
        description='Плановое ТО',
        work_cost=2000,
        parts_cost=5000,
        component_types=[ComponentType.ENGINE_OIL],
    )


def _update_request() -> RepairUpdateRequest:
    return RepairUpdateRequest(
        repair_date=date(2026, 1, 16),
        km_at_repair=16000,
        description='Повторное ТО',
        work_cost=3000,
        parts_cost=6000,
        component_types=[ComponentType.ENGINE_OIL],
    )


def test_create_repair_returns_response() -> None:
    db = MagicMock()
    request = _create_request()
    with patch('app.api.repair.handler.RepairService') as service_cls:
        service_cls.return_value.create.return_value = _repair()

        response = asyncio.run(
            RepairHandler().create_repair(request=request, db=db, vehicle=_vehicle())
        )

    assert isinstance(response, RepairResponse)
    assert response.id == 1
    assert response.work_cost == 2000
    assert response.component_types == [ComponentType.ENGINE_OIL]
    service_cls.return_value.create.assert_called_once_with(1, request, _vehicle())


def test_create_repair_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.repair.handler.RepairService') as service_cls:
        service_cls.return_value.create.side_effect = ValueError('Дата ремонта в будущем')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                RepairHandler().create_repair(
                    request=_create_request(),
                    db=db,
                    vehicle=_vehicle(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Дата ремонта в будущем'
    db.rollback.assert_called_once()


def test_create_repair_maps_unexpected_error_to_500() -> None:
    db = MagicMock()
    with patch('app.api.repair.handler.RepairService') as service_cls:
        service_cls.return_value.create.side_effect = RuntimeError('boom')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                RepairHandler().create_repair(
                    request=_create_request(),
                    db=db,
                    vehicle=_vehicle(),
                )
            )

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == 'Не удалось создать ремонт'
    db.rollback.assert_called_once()


def test_get_vehicle_repairs_returns_responses() -> None:
    db = MagicMock()
    with patch('app.api.repair.handler.RepairService') as service_cls:
        service_cls.return_value.get_by_vehicle.return_value = [_repair(1), _repair(2)]

        responses = asyncio.run(
            RepairHandler().get_vehicle_repairs(db=db, vehicle=_vehicle())
        )

    assert [item.id for item in responses] == [1, 2]
    service_cls.return_value.get_by_vehicle.assert_called_once_with(1)


def test_get_repair_returns_response() -> None:
    response = asyncio.run(RepairHandler().get_repair(repair=_repair()))

    assert isinstance(response, RepairResponse)
    assert response.id == 1
    assert response.repair_date == date(2026, 1, 15)
    assert response.km_at_repair == 15000


def test_update_repair_returns_response() -> None:
    db = MagicMock()
    request = _update_request()
    updated = _repair()
    updated.work_cost = 3000
    with patch('app.api.repair.handler.RepairService') as service_cls:
        service_cls.return_value.update.return_value = updated

        response = asyncio.run(
            RepairHandler().update_repair(
                request=request,
                db=db,
                repair=_repair(),
            )
        )

    assert response.work_cost == 3000
    service_cls.return_value.update.assert_called_once_with(1, request)


def test_update_repair_returns_404_when_disappeared() -> None:
    db = MagicMock()
    with patch('app.api.repair.handler.RepairService') as service_cls:
        service_cls.return_value.update.return_value = None

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                RepairHandler().update_repair(
                    request=_update_request(),
                    db=db,
                    repair=_repair(),
                )
            )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == 'Ремонт не найден'


def test_update_repair_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.repair.handler.RepairService') as service_cls:
        service_cls.return_value.update.side_effect = ValueError('Некорректный ремонт')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                RepairHandler().update_repair(
                    request=_update_request(),
                    db=db,
                    repair=_repair(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Некорректный ремонт'
    db.rollback.assert_called_once()


def test_delete_repair_returns_message() -> None:
    db = MagicMock()
    with patch('app.api.repair.handler.RepairService') as service_cls:
        response = asyncio.run(
            RepairHandler().delete_repair(db=db, repair=_repair())
        )

    assert response == {'status': 'ok', 'message': 'Ремонт 1 удалён'}
    service_cls.return_value.delete.assert_called_once_with(1)
