from typing import Final

from app.common.enums import StatusEnum, LiquidType
from app.common.liquid_config import LIQUIDS_CONFIG
from app.services.dto import VehicleDTO, ReplacementDTO

_OVERDUE: Final[int] = 250
_CRITICAL: Final[int] = 500
_WARNING: Final[int] = 1000
_LIQUID_FIELD: dict[LiquidType, str] = {cfg.type: cfg.interval_field for cfg in LIQUIDS_CONFIG}


class LiquidCalculator:
    """Калькулятор статусов замен жидкостей."""

    @staticmethod
    def calculate_status(
        km_at_replacement: int,
        interval_km: int,
        current_km: int,
    ) -> dict:
        """Рассчитать статус замены."""
        next_km = km_at_replacement + interval_km
        km_remaining = next_km - current_km

        if km_remaining < 0:
            status = StatusEnum.OVERDUE.value
            message = "🔴 ТРЕБУЕТСЯ НЕМЕДЛЕННАЯ ЗАМЕНА!"
        elif km_remaining <= _OVERDUE:
            status = StatusEnum.CRITICAL.value
            message = f"🔴 СРОЧНО! Осталось {km_remaining} км"
        elif km_remaining <= _CRITICAL:
            status = StatusEnum.CRITICAL.value
            message = f"🟠 КРИТИЧНО! Осталось {km_remaining} км"
        elif km_remaining <= _WARNING:
            status = StatusEnum.WARNING.value
            message = f"🟡 СКОРО ЗАМЕНА! Осталось {km_remaining} км"
        else:
            status = StatusEnum.GOOD.value
            message = f"🟢 В норме. Замена через {km_remaining} км"

        return {
            "next_replacement_km": next_km,
            "km_remaining": km_remaining,
            "status": status,
            "status_message": message
        }

    @staticmethod
    def get_vehicle_status(
        vehicle_dto: VehicleDTO,
        replacements: list,
    ) -> str:
        """Получить общий статус автомобиля."""
        if not replacements:
            return StatusEnum.UNKNOWN.value  # type: ignore[no-any-return]

        last_by_type: dict[LiquidType, ReplacementDTO] = {}
        for r in replacements:
            if r.liquid_type not in last_by_type or r.km_at_replacement > last_by_type[r.liquid_type].km_at_replacement:
                last_by_type[r.liquid_type] = r

        has_warning = False
        for r in last_by_type.values():
            interval = getattr(vehicle_dto, _LIQUID_FIELD[r.liquid_type])
            status = LiquidCalculator.calculate_status(
                r.km_at_replacement,
                interval,
                vehicle_dto.current_km)['status']
            if status == StatusEnum.OVERDUE.value:
                return StatusEnum.OVERDUE.value  # type: ignore[no-any-return]
            if status == StatusEnum.CRITICAL.value:
                return StatusEnum.CRITICAL.value  # type: ignore[no-any-return]
            if status == StatusEnum.WARNING.value:
                has_warning = True

        return StatusEnum.WARNING.value if has_warning else StatusEnum.GOOD.value  # type: ignore[no-any-return]
