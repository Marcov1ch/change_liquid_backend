import asyncio
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.share.handler import ShareHandler
from app.common.enums import ComponentType, StatusEnum
from app.services.dto import OtherExpenseDTO, RepairDTO, ReplacementDTO, VehicleDTO


def _vehicle(share_token: str | None = 'tok') -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='VW', model='Golf', brand_id=1, model_id=1,
        plate_number='А123АА178', year=2015, current_km=20000,
        is_active=True, owner_id=1,
        share_token=share_token,
        intervals={'engine_oil': 7000},
        notify_flags={},
    )


def _replacement() -> ReplacementDTO:
    return ReplacementDTO(
        id=1, vehicle_id=1,
        component_type=ComponentType.ENGINE_OIL,
        component_name='Mobil 1',
        component_price=5000,
        work_price=1500,
        replacement_date=date(2026, 1, 15),
        km_at_replacement=15000,
        interval_km=7000,
    )


def test_link_response_enabled() -> None:
    with (
        patch('app.api.share.handler.build_share_url', return_value='http://front/share/tok'),
        patch('app.api.share.handler.build_register_url', return_value='http://front/register'),
    ):
        response = ShareHandler._link_response('tok')

    assert response.enabled is True
    assert response.token == 'tok'
    assert response.share_url == 'http://front/share/tok'
    assert response.register_url == 'http://front/register'


def test_link_response_disabled() -> None:
    with patch('app.api.share.handler.build_register_url', return_value='http://front/register'):
        response = ShareHandler._link_response(None)

    assert response.enabled is False
    assert response.token is None
    assert response.share_url is None


def test_public_vehicle_returns_history_and_register_url() -> None:
    with (
        patch('app.api.share.handler.VehicleShareService') as share_service_cls,
        patch('app.api.share.handler.ReplacementService') as replacement_service_cls,
        patch('app.api.share.handler.OtherExpenseService') as other_expense_service_cls,
        patch('app.api.share.handler.RepairService') as repair_service_cls,
        patch('app.api.share.handler.build_register_url', return_value='http://front/register'),
    ):
        share_service_cls.return_value.find_by_token.return_value = _vehicle()
        replacement_service = replacement_service_cls.return_value
        replacement_service.get_by_vehicle.return_value = [_replacement()]
        replacement_service.get_latest_replacement_ids.return_value = {1}
        other_expense_service_cls.return_value.get_by_vehicle.return_value = [
            OtherExpenseDTO(
                id=1,
                vehicle_id=1,
                name='Штраф',
                expense_date=date(2026, 1, 20),
                amount=500,
            ),
        ]
        repair_service_cls.return_value.get_by_vehicle.return_value = [
            RepairDTO(
                id=1,
                vehicle_id=1,
                repair_date=date(2026, 1, 18),
                km_at_repair=14000,
                description='Замена масла',
                work_cost=2000,
                parts_cost=5000,
                component_types=[ComponentType.ENGINE_OIL],
            ),
        ]

        response = asyncio.run(
            ShareHandler().get_public_vehicle('tok', db=MagicMock())
        )

    assert response.brand == 'VW'
    assert response.plate_number == 'А123АА178'
    assert response.vehicle_status == StatusEnum.GOOD.value
    assert response.register_url == 'http://front/register'
    assert len(response.replacements) == 1
    assert response.replacements[0].component_price == 5000
    assert response.replacements[0].status == StatusEnum.GOOD
    assert not hasattr(response.replacements[0], 'vehicle_id')
    assert len(response.other_expenses) == 1
    assert response.other_expenses[0].name == 'Штраф'
    assert response.other_expenses[0].amount == 500
    assert not hasattr(response.other_expenses[0], 'vehicle_id')
    assert len(response.repairs) == 1
    assert response.repairs[0].km_at_repair == 14000
    assert response.repairs[0].work_cost == 2000
    assert response.repairs[0].parts_cost == 5000
    assert not hasattr(response.repairs[0], 'vehicle_id')


def test_public_vehicle_not_found() -> None:
    with patch('app.api.share.handler.VehicleShareService') as share_service_cls:
        share_service_cls.return_value.find_by_token.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(ShareHandler().get_public_vehicle('missing', db=MagicMock()))

    assert exc_info.value.status_code == 404
