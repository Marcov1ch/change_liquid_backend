from datetime import date

import pytest
from pydantic import ValidationError

from app.api.vehicle.schema import UpdateVehicleData


@pytest.mark.parametrize(
    ("year", "should_pass"),
    [
        pytest.param(None, True, id="none_omitted"),
        pytest.param(1960, True, id="lower_bound"),
        pytest.param(date.today().year, True, id="current_year"),
        pytest.param(date.today().year + 1, True, id="next_year"),
        pytest.param(1959, False, id="below_lower_bound"),
        pytest.param(date.today().year + 2, False, id="far_future"),
    ],
)
def test_update_vehicle_data_year_validation(
    year: int | None,
    should_pass: bool,
) -> None:
    if should_pass:
        assert UpdateVehicleData(year=year).year == year
    else:
        with pytest.raises(ValidationError):
            UpdateVehicleData(year=year)
