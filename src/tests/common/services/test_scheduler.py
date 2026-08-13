from datetime import date

from app.services.scheduler import _resolve_next_change_date


def test_tire_uses_stored_date() -> None:
    vehicle = {"interval_months": {}}
    last = {
        "component_type": "tire_change",
        "replacement_date": date(2026, 1, 1),
        "next_change_date": date(2026, 11, 1),
    }
    assert _resolve_next_change_date(vehicle, last) == date(2026, 11, 1)


def test_non_tire_computed_from_vehicle_months() -> None:
    vehicle = {"interval_months": {"engine_oil": 13}}
    last = {
        "component_type": "engine_oil",
        "replacement_date": date(2026, 1, 15),
        "next_change_date": None,
    }
    assert _resolve_next_change_date(vehicle, last) == date(2027, 2, 15)


def test_non_tire_without_months_returns_none() -> None:
    vehicle = {"interval_months": {}}
    last = {
        "component_type": "engine_oil",
        "replacement_date": date(2026, 1, 15),
        "next_change_date": None,
    }
    assert _resolve_next_change_date(vehicle, last) is None


def test_non_tire_without_replacement_date_returns_none() -> None:
    vehicle = {"interval_months": {"engine_oil": 12}}
    last = {
        "component_type": "engine_oil",
        "replacement_date": None,
        "next_change_date": None,
    }
    assert _resolve_next_change_date(vehicle, last) is None
