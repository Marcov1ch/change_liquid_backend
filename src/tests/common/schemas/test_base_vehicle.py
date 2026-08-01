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
