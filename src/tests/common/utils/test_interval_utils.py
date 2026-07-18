import pytest

from typing import Any

from app.common.enums import ComponentType
from app.common.utils.interval_utils import ComponentIntervalUtils
from app.services.dto import VehicleDTO


def _vehicle(intervals: dict | None = None, **kwargs: Any) -> VehicleDTO:
    return VehicleDTO(
        id=1, brand='', model='', brand_id=1, model_id=1,
        plate_number='', year=2000, current_km=20000,
        is_active=True, owner_id=1,
        intervals=intervals or {},
        notify_flags={},
        **kwargs,
    )


@pytest.mark.parametrize(
    ("vehicle", "component_type", "expected"),
    [
        pytest.param(
            _vehicle(intervals={'engine_oil': 7000}),
            ComponentType.ENGINE_OIL,
            7000,
            id="existing_component",
        ),
        pytest.param(
            _vehicle(intervals={'engine_oil': 7000}),
            ComponentType.COOLANT,
            0,
            id="missing_component",
        ),
        pytest.param(
            _vehicle(),
            ComponentType.ENGINE_OIL,
            0,
            id="empty_intervals",
        ),
    ],
)
def test_get_interval_for_component(
    vehicle: VehicleDTO, component_type: ComponentType, expected: int,
) -> None:
    assert ComponentIntervalUtils.get_interval_for_component(vehicle, component_type) == expected


ALL_COMPONENTS = list(ComponentType)


@pytest.mark.parametrize(
    ("vehicle", "expected_engine_oil", "expected_brake_fluid", "all_zero"),
    [
        pytest.param(
            _vehicle(intervals={'engine_oil': 7000, 'brake_fluid': 40000}),
            7000, 40000, False,
            id="all_types",
        ),
        pytest.param(
            _vehicle(),
            0, 0, True,
            id="all_zero",
        ),
    ],
)
def test_get_all_intervals(
    vehicle: VehicleDTO,
    expected_engine_oil: int,
    expected_brake_fluid: int,
    all_zero: bool,
) -> None:
    result = ComponentIntervalUtils.get_all_intervals(vehicle)
    assert len(result) == len(ALL_COMPONENTS)
    assert result[ComponentType.ENGINE_OIL] == expected_engine_oil
    assert result[ComponentType.BRAKE_FLUID] == expected_brake_fluid
    if all_zero:
        assert all(v == 0 for v in result.values())
