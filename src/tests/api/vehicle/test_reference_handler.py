import asyncio
from unittest.mock import MagicMock, patch

from app.api.vehicle.handler import VehicleHandler
from app.api.vehicle.schema import UpdateVehicleReference
from app.services.dto import VehicleDTO


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
        reference_items=[
            {
                'component_type': 'engine_oil',
                'volume_liters': 5.7,
                'note': None,
                'variants': [{'name': '0W-20', 'approvals': 'VW 508 00'}],
            },
        ],
    )


def test_update_reference_replaces_items_and_returns_them() -> None:
    request = UpdateVehicleReference(reference_items=[
        {
            'component_type': 'engine_oil',
            'volume_liters': 5.7,
            'variants': [{'name': '0W-20', 'approvals': 'VW 508 00'}],
        },
    ])

    with patch('app.api.vehicle.handler.VehicleService') as vehicle_service_cls:
        service = vehicle_service_cls.return_value
        service.repository.replace_reference.return_value = _vehicle()

        response = asyncio.run(
            VehicleHandler().update_reference(
                request=request,
                db=MagicMock(),
                vehicle=_vehicle(),
            )
        )

    service.repository.replace_reference.assert_called_once_with(
        1,
        [
            {
                'component_type': 'engine_oil',
                'volume_liters': 5.7,
                'note': None,
                'variants': [{'name': '0W-20', 'approvals': 'VW 508 00'}],
            },
        ],
    )
    assert response.reference_items[0].component_type == 'engine_oil'
    assert response.reference_items[0].variants[0].name == '0W-20'
