import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette import status

from app.api.vehicle.handler import VehicleHandler
from app.api.vehicle.schema import UpdateVehicleData
from app.common.exceptions import VehicleConflictError
from app.services.dto import VehicleDTO
from app.services.notification_service import check_vehicle_notifications_background


def _vehicle() -> VehicleDTO:
    return VehicleDTO(
        id=1,
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


def _run_update(
    request: UpdateVehicleData,
    tasks: BackgroundTasks | None = None,
) -> tuple[MagicMock, MagicMock]:
    tasks = tasks or BackgroundTasks()
    with (
        patch('app.api.vehicle.handler.VehicleService') as vehicle_service_cls,
        patch('app.api.vehicle.handler.ReplacementService') as replacement_service_cls,
    ):
        vehicle_service = vehicle_service_cls.return_value
        vehicle_service.partial_update.return_value = _vehicle()

        asyncio.run(
            VehicleHandler().update_vehicle(
                request=request,
                background_tasks=tasks,
                db=MagicMock(),
                vehicle=_vehicle(),
            )
        )

    return vehicle_service, replacement_service_cls.return_value


def test_update_vehicle_passes_only_changed_fields() -> None:
    service, _ = _run_update(
        UpdateVehicleData(year=2020, intervals={'engine_oil': 9000})
    )

    service.partial_update.assert_called_once_with(
        _vehicle(),
        {'year': 2020, 'intervals': {'engine_oil': 9000}},
    )
    service.update_brand_model.assert_not_called()


def test_update_vehicle_keeps_nested_none_values() -> None:
    service, replacement_service = _run_update(
        UpdateVehicleData(interval_months={'engine_oil': None})
    )

    service.partial_update.assert_called_once_with(
        _vehicle(),
        {'interval_months': {'engine_oil': None}},
    )
    replacement_service.reset_date_notify_flags.assert_called_once_with(1)


def test_update_vehicle_schedules_notification_on_km_change() -> None:
    tasks = BackgroundTasks()
    _run_update(UpdateVehicleData(current_km=25000), tasks)

    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func is check_vehicle_notifications_background
    assert tasks.tasks[0].args == (1,)


def test_update_vehicle_maps_conflict_to_409() -> None:
    with patch('app.api.vehicle.handler.VehicleService') as vehicle_service_cls:
        vehicle_service_cls.return_value.partial_update.side_effect = VehicleConflictError(
            'занят'
        )

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                VehicleHandler().update_vehicle(
                    request=UpdateVehicleData(plate_number='В456ВВ178'),
                    background_tasks=BackgroundTasks(),
                    db=MagicMock(),
                    vehicle=_vehicle(),
                )
            )

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT


def test_update_vehicle_maps_validation_to_400() -> None:
    with patch('app.api.vehicle.handler.VehicleService') as vehicle_service_cls:
        vehicle_service_cls.return_value.partial_update.side_effect = ValueError('bad km')

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                VehicleHandler().update_vehicle(
                    request=UpdateVehicleData(current_km=100),
                    background_tasks=BackgroundTasks(),
                    db=MagicMock(),
                    vehicle=_vehicle(),
                )
            )

    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
