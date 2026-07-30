from datetime import date
from typing import Final

from app.common.enums import StatusEnum, ComponentType
from app.services.dto import VehicleDTO, ReplacementDTO

_OVERDUE: Final[int] = 250
_CRITICAL: Final[int] = 500
_WARNING: Final[int] = 1000

_DATE_WARNING_DAYS: Final[int] = 5


class StatusCalculator:
    """Калькулятор статусов замен."""

    @staticmethod
    def calculate_date_status(
        next_change_date: date | None,
    ) -> dict:
        """Рассчитать статус замены по дате (для шин и date-based компонентов)."""
        if next_change_date is None:
            return {
                "next_change_date": None,
                "days_remaining": None,
                "status": StatusEnum.UNKNOWN.value,
                "status_message": "🟡 Дата не указана",
            }

        today = date.today()
        days_remaining = (next_change_date - today).days

        if days_remaining < 0:
            status = StatusEnum.OVERDUE.value
            message = f"🔴 ПРОСРОЧЕНО на {-days_remaining} дн."
        elif days_remaining <= _DATE_WARNING_DAYS:
            status = StatusEnum.WARNING.value
            message = f"🟡 СКОРО! Осталось {days_remaining} дн."
        else:
            status = StatusEnum.GOOD.value
            message = f"🟢 Замена через {days_remaining} дн."

        return {
            "next_change_date": next_change_date,
            "days_remaining": days_remaining,
            "status": status,
            "status_message": message,
        }

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

        last_by_type: dict[ComponentType, ReplacementDTO] = {}
        for replacement in replacements:
            prev = last_by_type.get(replacement.component_type)
            if prev is None:
                last_by_type[replacement.component_type] = replacement
            elif replacement.km_at_replacement > prev.km_at_replacement:
                last_by_type[replacement.component_type] = replacement
            elif replacement.km_at_replacement == prev.km_at_replacement and (replacement.id or 0) > (prev.id or 0):
                last_by_type[replacement.component_type] = replacement

        has_warning = False
        for replacement in last_by_type.values():
            if replacement.component_type == ComponentType.TIRE_CHANGE:
                date_result = StatusCalculator.calculate_date_status(replacement.next_change_date)
                status = date_result['status']
            else:
                interval = vehicle_dto.intervals.get(replacement.component_type.value)
                if interval is None:
                    continue
                status = StatusCalculator.calculate_status(
                    replacement.km_at_replacement,
                    interval,
                    vehicle_dto.current_km)['status']
            if status == StatusEnum.OVERDUE.value:
                return StatusEnum.OVERDUE.value  # type: ignore[no-any-return]
            if status == StatusEnum.CRITICAL.value:
                return StatusEnum.CRITICAL.value  # type: ignore[no-any-return]
            if status == StatusEnum.WARNING.value:
                has_warning = True

        return StatusEnum.WARNING.value if has_warning else StatusEnum.GOOD.value  # type: ignore[no-any-return]
