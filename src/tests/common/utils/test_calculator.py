import pytest

from app.common.enums import StatusEnum
from app.common.utils.calculator import StatusCalculator


def _expected_next(km_at: int, interval: int) -> int:
    return km_at + interval


@pytest.mark.parametrize(
    ("km_at", "interval", "current_km", "exp_remaining", "exp_status"),
    [
        pytest.param(1000, 5000, 6000, 0, StatusEnum.CRITICAL.value, id="critical_0"),
        pytest.param(1000, 5000, 7500, -1500, StatusEnum.OVERDUE.value, id="overdue_negative"),
        pytest.param(1000, 5000, 5750, 250, StatusEnum.CRITICAL.value, id="critical_srochno_250"),
        pytest.param(1000, 5000, 5999, 1, StatusEnum.CRITICAL.value, id="critical_srochno_1"),
        pytest.param(1000, 5000, 5500, 500, StatusEnum.CRITICAL.value, id="critical_kritichno_500"),
        pytest.param(1000, 5000, 5600, 400, StatusEnum.CRITICAL.value, id="critical_kritichno_400"),
        pytest.param(1000, 5000, 5000, 1000, StatusEnum.WARNING.value, id="warning_1000"),
        pytest.param(1000, 5000, 5200, 800, StatusEnum.WARNING.value, id="warning_800"),
        pytest.param(1000, 5000, 4999, 1001, StatusEnum.GOOD.value, id="good_1001"),
        pytest.param(1000, 5000, 3000, 3000, StatusEnum.GOOD.value, id="good_3000"),
        pytest.param(1000, 5000, 1000, 5000, StatusEnum.GOOD.value, id="just_replaced"),
        pytest.param(10000, 0, 10000, 0, StatusEnum.CRITICAL.value, id="zero_interval"),
        pytest.param(10000, 0, 10001, -1, StatusEnum.OVERDUE.value, id="zero_interval_overdue"),
    ],
)
def test_calculate_status(
    km_at: int, interval: int, current_km: int,
    exp_remaining: int, exp_status: str,
) -> None:
    result = StatusCalculator.calculate_status(km_at, interval, current_km)
    assert result["km_remaining"] == exp_remaining
    assert result["status"] == exp_status
    assert result["next_replacement_km"] == _expected_next(km_at, interval)
    assert "status_message" in result
