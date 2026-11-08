from datetime import date

import pytest
from pydantic import ValidationError

from app.api.vehicle.schema import RimSize, TireSize, UpdateVehicleData, UpdateVehicleSizes


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


def test_update_vehicle_data_normalizes_plate_number() -> None:
    payload = UpdateVehicleData(plate_number='  ab-123-cd  ')
    assert payload.plate_number == 'AB-123-CD'


def test_update_vehicle_data_plate_number_none_is_allowed() -> None:
    assert UpdateVehicleData(plate_number=None).plate_number is None


def test_update_vehicle_data_rejects_too_long_plate_number() -> None:
    with pytest.raises(ValidationError):
        UpdateVehicleData(plate_number='A' * 16)


def test_update_vehicle_data_rejects_empty_plate_number() -> None:
    with pytest.raises(ValidationError):
        UpdateVehicleData(plate_number='   ')


def test_rim_size_valid() -> None:
    rim = RimSize(
        diameter=16,
        pcd='5x114.3',
        et_from=45,
        et_to=50,
        width_from=6,
        width_to=6.5,
    )
    assert rim.diameter == 16
    assert rim.et_to == 50
    assert rim.width_to == 6.5


def test_rim_size_fully_optional() -> None:
    rim = RimSize(diameter=15)
    assert rim.pcd is None
    assert rim.et_from is None


def test_rim_size_et_range_invalid() -> None:
    with pytest.raises(ValidationError):
        RimSize(et_from=50, et_to=45)


def test_rim_size_width_range_invalid() -> None:
    with pytest.raises(ValidationError):
        RimSize(width_from=6.5, width_to=6)


def test_tire_size_valid() -> None:
    tire = TireSize(size='215/65 R16', label='лето')
    assert tire.size == '215/65 R16'
    assert tire.label == 'лето'


def test_tire_size_requires_size() -> None:
    with pytest.raises(ValidationError):
        TireSize(label='лето')


def test_update_vehicle_sizes_roundtrip() -> None:
    payload = UpdateVehicleSizes(
        rims=[RimSize(diameter=15, width_from=6, width_to=6.5)],
        tires=[TireSize(size='205/75 R15')],
    )
    assert len(payload.rims) == 1
    assert len(payload.tires) == 1
    assert payload.rims[0].diameter == 15
    assert payload.tires[0].size == '205/75 R15'


def test_update_vehicle_sizes_defaults_empty() -> None:
    payload = UpdateVehicleSizes()
    assert payload.rims == []
    assert payload.tires == []
