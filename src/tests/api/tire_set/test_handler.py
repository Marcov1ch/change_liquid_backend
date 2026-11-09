import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status

from app.api.tire_set.handler import TireSetHandler
from app.api.tire_set.schema import (
    TireInstallRequest,
    TireInstallResponse,
    TireSetCreateRequest,
    TireSetResponse,
    TireSetUpdateRequest,
)
from app.common.enums import ComponentType, TireSeason
from app.services.dto import ReplacementDTO, TireSetDTO, VehicleDTO


def _vehicle() -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='VW', model='Golf', brand_id=1, model_id=1,
        plate_number='А123АА178', year=2015, current_km=20000,
        is_active=True, owner_id=1,
    )


def _tire_set(tire_set_id: int = 1) -> TireSetDTO:
    return TireSetDTO(
        id=tire_set_id,
        vehicle_id=1,
        name='Зимние Michelin',
        season='winter',
        purchase_date=date(2026, 10, 17),
        purchase_price=30000,
        accumulated_km=5000,
        installed_km=20000,
        installed_date=date(2026, 10, 17),
        is_installed=True,
        next_change_date=date(2027, 4, 17),
        status='good',
        days_remaining=180,
        total_km=5000,
    )


def _replacement() -> ReplacementDTO:
    return ReplacementDTO(
        id=10,
        vehicle_id=1,
        component_type=ComponentType.TIRE_CHANGE,
        component_name='Зимние Michelin',
        component_price=None,
        work_price=1500,
        replacement_date=date(2026, 10, 17),
        km_at_replacement=20000,
        interval_km=0,
        next_change_date=date(2027, 4, 17),
        tire_set_id=1,
        tire_event_type='install',
    )


def _create_request() -> TireSetCreateRequest:
    return TireSetCreateRequest(
        name='Зимние Michelin',
        season='winter',
        purchase_date=date(2026, 10, 17),
        purchase_price=30000,
        install_now=True,
        work_price=1500,
    )


def test_get_tire_sets_returns_responses() -> None:
    db = MagicMock()
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.get_by_vehicle.return_value = [_tire_set(1), _tire_set(2)]

        responses = asyncio.run(
            TireSetHandler().get_tire_sets(db=db, vehicle=_vehicle())
        )

    assert [item.id for item in responses] == [1, 2]
    assert responses[0].season == TireSeason.WINTER
    service_cls.return_value.get_by_vehicle.assert_called_once_with(1, 20000)


def test_create_tire_set_returns_response() -> None:
    db = MagicMock()
    request = _create_request()
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.create.return_value = _tire_set()

        response = asyncio.run(
            TireSetHandler().create_tire_set(
                request=request,
                db=db,
                vehicle=_vehicle(),
            )
        )

    assert isinstance(response, TireSetResponse)
    assert response.name == 'Зимние Michelin'
    assert response.is_installed is True
    assert response.total_km == 5000
    service_cls.return_value.create.assert_called_once_with(1, request, _vehicle())


def test_create_tire_set_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.create.side_effect = ValueError('Некорректный комплект')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                TireSetHandler().create_tire_set(
                    request=_create_request(),
                    db=db,
                    vehicle=_vehicle(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Некорректный комплект'


def test_update_tire_set_returns_response() -> None:
    db = MagicMock()
    request = TireSetUpdateRequest(name='Зимние 2')
    updated = _tire_set()
    updated.name = 'Зимние 2'
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.update.return_value = updated

        response = asyncio.run(
            TireSetHandler().update_tire_set(
                request=request,
                db=db,
                tire_set=_tire_set(),
            )
        )

    assert response.name == 'Зимние 2'
    service_cls.return_value.update.assert_called_once_with(1, request)


def test_update_tire_set_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.update.side_effect = ValueError('Комплект в архиве')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                TireSetHandler().update_tire_set(
                    request=TireSetUpdateRequest(name='Зимние 2'),
                    db=db,
                    tire_set=_tire_set(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Комплект в архиве'


def test_delete_tire_set_returns_message() -> None:
    db = MagicMock()
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        response = asyncio.run(
            TireSetHandler().delete_tire_set(db=db, tire_set=_tire_set())
        )

    assert response == {'status': 'ok', 'message': 'Комплект шин 1 удалён'}
    service_cls.return_value.delete.assert_called_once_with(1)


def test_delete_tire_set_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.delete.side_effect = ValueError(
            'Нельзя удалить установленный комплект шин'
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                TireSetHandler().delete_tire_set(db=db, tire_set=_tire_set())
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Нельзя удалить установленный комплект шин'


def test_install_tire_set_returns_response() -> None:
    db = MagicMock()
    request = TireInstallRequest(work_price=1500)
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.install.return_value = (
            _tire_set(),
            _replacement(),
        )

        response = asyncio.run(
            TireSetHandler().install_tire_set(
                tire_set_id=1,
                request=request,
                db=db,
                vehicle=_vehicle(),
            )
        )

    assert isinstance(response, TireInstallResponse)
    assert response.tire_set.id == 1
    assert response.replacement.id == 10
    assert response.replacement.component_type == ComponentType.TIRE_CHANGE
    assert response.replacement.work_price == 1500
    service_cls.return_value.install.assert_called_once_with(
        1, 1, request, _vehicle(),
    )


def test_install_tire_set_maps_value_error_to_400() -> None:
    db = MagicMock()
    with patch('app.api.tire_set.handler.TireSetService') as service_cls:
        service_cls.return_value.install.side_effect = ValueError(
            'Этот комплект шин уже установлен'
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                TireSetHandler().install_tire_set(
                    tire_set_id=1,
                    request=TireInstallRequest(),
                    db=db,
                    vehicle=_vehicle(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Этот комплект шин уже установлен'
