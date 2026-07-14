import pytest

from app.common.enums import StatusEnum
from app.common.utils.calculator import LiquidCalculator

km_at = 1000
interval = 5000
next_km = km_at + interval


@pytest.mark.parametrize(
    (
        "current_km",
        "exp_remaining",
        "exp_status",
    ),
    [
        pytest.param(
            next_km,
            0,
            StatusEnum.CRITICAL.value,
            id="critical_0",
        ),
        pytest.param(
            7500,
            -1500,
            StatusEnum.OVERDUE.value,
            id="overdue_negative",
        ),
        pytest.param(
            next_km - 250,
            250,
            StatusEnum.CRITICAL.value,
            id="critical_srochno_250",
        ),
        pytest.param(
            next_km - 1,
            1,
            StatusEnum.CRITICAL.value,
            id="critical_srochno_1",
        ),
        pytest.param(
            next_km - 500,
            500,
            StatusEnum.CRITICAL.value,
            id="critical_kritichno_500"),
        pytest.param(
            next_km - 400,
            400,
            StatusEnum.CRITICAL.value,
            id="critical_kritichno_400"),
        pytest.param(
            next_km - 1000,
            1000,
            StatusEnum.WARNING.value,
            id="warning_1000",
        ),
        pytest.param(
            next_km - 800,
            800,
            StatusEnum.WARNING.value,
            id="warning_800",
        ),
        pytest.param(
            next_km - 1001,
            1001,
            StatusEnum.GOOD.value,
            id="good_1001",
        ),
        pytest.param(
            3000,
            next_km - 3000,
            StatusEnum.GOOD.value,
            id="good_3000",
        ),
    ],
)
def test_calculate_status(current_km: int, exp_remaining: int, exp_status: str) -> None:
    result = LiquidCalculator.calculate_status(km_at, interval, current_km)
    assert result["km_remaining"] == exp_remaining
    assert result["status"] == exp_status
    assert result["next_replacement_km"] == next_km
    assert "status_message" in result
