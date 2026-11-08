import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette import status

from app.api.other_expense.handler import OtherExpenseHandler
from app.api.other_expense.schema import (
    OtherExpenseCreateRequest,
    OtherExpenseResponse,
    OtherExpenseUpdateRequest,
)
from app.services.dto import OtherExpenseDTO, VehicleDTO


def _vehicle(is_active: bool = True) -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='VW', model='Golf', brand_id=1, model_id=1,
        plate_number='А123АА178', year=2015, current_km=20000,
        is_active=is_active, owner_id=1,
    )


def _expense(expense_id: int = 1) -> OtherExpenseDTO:
    return OtherExpenseDTO(
        id=expense_id,
        vehicle_id=1,
        name='Штраф',
        expense_date=date(2026, 1, 15),
        amount=500,
    )


def test_create_other_expense_returns_response() -> None:
    db = MagicMock()
    with patch('app.api.other_expense.handler.OtherExpenseService') as service_cls:
        service_cls.return_value.create.return_value = _expense()

        response = asyncio.run(
            OtherExpenseHandler().create_other_expense(
                request=OtherExpenseCreateRequest(
                    name='Штраф',
                    expense_date=date(2026, 1, 15),
                    amount=500,
                ),
                db=db,
                vehicle=_vehicle(),
            )
        )

    assert isinstance(response, OtherExpenseResponse)
    assert response.id == 1
    assert response.name == 'Штраф'
    assert response.amount == 500
    service_cls.return_value.create.assert_called_once()
    assert service_cls.return_value.create.call_args[0][0] == 1


def test_create_maps_validation_error_to_400() -> None:
    db = MagicMock()
    request = SimpleNamespace(name='Штраф', expense_date=date(2026, 1, 15), amount=0)
    with patch('app.api.other_expense.handler.OtherExpenseService') as service_cls:
        service_cls.return_value.create.side_effect = ValueError('Стоимость траты должна быть больше 0')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                OtherExpenseHandler().create_other_expense(
                    request=request,
                    db=db,
                    vehicle=_vehicle(),
                )
            )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == 'Стоимость траты должна быть больше 0'


def test_get_vehicle_other_expenses_returns_responses() -> None:
    db = MagicMock()
    with patch('app.api.other_expense.handler.OtherExpenseService') as service_cls:
        service_cls.return_value.get_by_vehicle.return_value = [_expense(1), _expense(2)]

        responses = asyncio.run(
            OtherExpenseHandler().get_vehicle_other_expenses(db=db, vehicle=_vehicle())
        )

    assert [r.id for r in responses] == [1, 2]
    service_cls.return_value.get_by_vehicle.assert_called_once_with(1)


def test_get_other_expense_returns_response() -> None:
    response = asyncio.run(
        OtherExpenseHandler().get_other_expense(db=MagicMock(), expense=_expense())
    )

    assert isinstance(response, OtherExpenseResponse)
    assert response.id == 1
    assert response.expense_date == date(2026, 1, 15)


def test_update_other_expense_returns_response() -> None:
    db = MagicMock()
    with patch('app.api.other_expense.handler.OtherExpenseService') as service_cls:
        updated = _expense()
        updated.amount = 700
        service_cls.return_value.update.return_value = updated

        response = asyncio.run(
            OtherExpenseHandler().update_other_expense(
                request=OtherExpenseUpdateRequest(amount=700),
                db=db,
                expense=_expense(),
            )
        )

    assert response.amount == 700
    service_cls.return_value.update.assert_called_once_with(1, amount=700)


def test_update_returns_404_when_expense_disappeared() -> None:
    db = MagicMock()
    with patch('app.api.other_expense.handler.OtherExpenseService') as service_cls:
        service_cls.return_value.update.return_value = None

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                OtherExpenseHandler().update_other_expense(
                    request=OtherExpenseUpdateRequest(amount=700),
                    db=db,
                    expense=_expense(),
                )
            )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


def test_delete_other_expense_returns_message() -> None:
    db = MagicMock()
    with patch('app.api.other_expense.handler.OtherExpenseService') as service_cls:
        response = asyncio.run(
            OtherExpenseHandler().delete_other_expense(db=db, expense=_expense())
        )

    assert response == {'status': 'ok', 'message': 'Трата 1 удалена'}
    service_cls.return_value.delete.assert_called_once_with(1)
