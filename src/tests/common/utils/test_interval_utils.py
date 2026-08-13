import pytest

from datetime import date
from typing import Any

from app.common.enums import ComponentType
from app.common.utils.interval_utils import ComponentIntervalUtils, add_months
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


ALL_COMPONENTS = [c for c in ComponentType if c != ComponentType.TIRE_CHANGE]


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


@pytest.mark.parametrize(
    ("source", "months", "expected"),
    [
        pytest.param(date(2026, 1, 15), 12, date(2027, 1, 15), id="plus_12"),
        pytest.param(date(2026, 1, 31), 1, date(2026, 2, 28), id="jan31_plus_1"),
        pytest.param(date(2024, 1, 31), 1, date(2024, 2, 29), id="leap_year"),
        pytest.param(date(2026, 3, 31), 1, date(2026, 4, 30), id="apr30"),
        pytest.param(date(2026, 12, 15), 2, date(2027, 2, 15), id="cross_year"),
        pytest.param(date(2026, 6, 1), 0, date(2026, 6, 1), id="zero"),
    ],
)
def test_add_months(source: date, months: int, expected: date) -> None:
    assert add_months(source, months) == expected


def test_add_months_negative_raises() -> None:
    with pytest.raises(ValueError):
        add_months(date(2026, 1, 1), -1)


def test_get_interval_months_for_component_none() -> None:
    vehicle = _vehicle(interval_months={})
    assert ComponentIntervalUtils.get_interval_months_for_component(
        vehicle, ComponentType.ENGINE_OIL,
    ) is None


def test_get_interval_months_for_component_set() -> None:
    vehicle = _vehicle(interval_months={'engine_oil': 12})
    assert ComponentIntervalUtils.get_interval_months_for_component(
        vehicle, ComponentType.ENGINE_OIL,
    ) == 12


def test_get_next_change_date() -> None:
    vehicle = _vehicle(interval_months={'engine_oil': 12})
    assert ComponentIntervalUtils.get_next_change_date(
        vehicle, ComponentType.ENGINE_OIL, date(2026, 1, 15),
    ) == date(2027, 1, 15)


def test_get_next_change_date_none() -> None:
    vehicle = _vehicle(interval_months={})
    assert ComponentIntervalUtils.get_next_change_date(
        vehicle, ComponentType.ENGINE_OIL, date(2026, 1, 15),
    ) is None
