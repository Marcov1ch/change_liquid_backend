from datetime import date

import pytest
from pydantic import ValidationError

from app.common.schemas.base_vehicle import VehicleBase


def _make(year: int) -> VehicleBase:
    return VehicleBase(
        brand='Toyota',
        model='Camry',
        plate_number='А123АА178',
        year=year,
        current_km=1000,
    )


@pytest.mark.parametrize(
    ("year", "should_pass"),
    [
        pytest.param(1960, True, id="lower_bound"),
        pytest.param(2000, True, id="mid"),
        pytest.param(date.today().year, True, id="current_year"),
        pytest.param(date.today().year + 1, True, id="next_year"),
        pytest.param(1959, False, id="below_lower_bound"),
        pytest.param(date.today().year + 2, False, id="far_future"),
    ],
)
def test_vehicle_base_year_validation(year: int, should_pass: bool) -> None:
    if should_pass:
        assert _make(year).year == year
    else:
        with pytest.raises(ValidationError):
            _make(year)


def _with_plate(plate_number: str) -> VehicleBase:
    return VehicleBase(
        brand='Toyota',
        model='Camry',
        plate_number=plate_number,
        year=2000,
        current_km=1000,
    )


@pytest.mark.parametrize(
    ('plate', 'expected'),
    [
        pytest.param('А123АА178', 'А123АА178', id='rf'),
        pytest.param('ab-123-cd', 'AB-123-CD', id='european'),
        pytest.param('  AB 123 CD  ', 'AB 123 CD', id='spaces_preserved'),
        pytest.param('A' * 15, 'A' * 15, id='max_length'),
    ],
)
def test_plate_number_accepts_free_format(plate: str, expected: str) -> None:
    assert _with_plate(plate).plate_number == expected


@pytest.mark.parametrize(
    'plate',
    [
        pytest.param('', id='empty'),
        pytest.param('   ', id='spaces_only'),
        pytest.param('A' * 16, id='too_long'),
        pytest.param('AB\tCD', id='control_char'),
    ],
)
def test_plate_number_rejects_invalid_values(plate: str) -> None:
    with pytest.raises(ValidationError):
        _with_plate(plate)
