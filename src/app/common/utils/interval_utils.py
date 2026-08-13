from datetime import date

from app.common.enums import ComponentType
from app.common.component_config import COMPONENTS_CONFIG
from app.services.dto import ReplacementDTO, VehicleDTO


def add_months(source: date, months: int) -> date:
    """Прибавить к дате количество месяцев с учётом переполнения дней.

    Например: 2026-01-31 + 1 мес -> 2026-02-28.
    """
    if months < 0:
        raise ValueError('Количество месяцев не может быть отрицательным')

    month_index = source.month - 1 + months
    year = source.year + month_index // 12
    month = month_index % 12 + 1

    if month == 2:
        max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    elif month in (4, 6, 9, 11):
        max_day = 30
    else:
        max_day = 31

    day = min(source.day, max_day)
    return date(year, month, day)


def get_last_per_type(
    replacements: list[ReplacementDTO],
) -> dict[ComponentType, ReplacementDTO]:
    """Вернуть последнюю замену по каждому типу.

    Последняя = max(km_at_replacement), при равных — max(id).
    """
    last_by_type: dict[ComponentType, ReplacementDTO] = {}
    for replacement in replacements:
        prev = last_by_type.get(replacement.component_type)
        if prev is None:
            last_by_type[replacement.component_type] = replacement
        elif replacement.km_at_replacement > prev.km_at_replacement:
            last_by_type[replacement.component_type] = replacement
        elif replacement.km_at_replacement == prev.km_at_replacement and (replacement.id or 0) > (prev.id or 0):  # noqa: E501
            last_by_type[replacement.component_type] = replacement
    return last_by_type


class ComponentIntervalUtils:
    """Утилиты для работы с интервалами замен."""

    @staticmethod
    def get_interval_for_component(
        vehicle_dto: VehicleDTO,
        component_type: ComponentType,
    ) -> int:
        """Получить интервал замены для компонента из настроек автомобиля."""
        return vehicle_dto.intervals.get(component_type.value, 0)  # type: ignore[no-any-return]

    @staticmethod
    def get_interval_months_for_component(
        vehicle_dto: VehicleDTO,
        component_type: ComponentType,
    ) -> int | None:
        """Получить месячный интервал замены для компонента из настроек авто."""
        months = vehicle_dto.interval_months.get(component_type.value)
        if months is None:
            return None
        return months  # type: ignore[no-any-return]

    @staticmethod
    def get_next_change_date(
        vehicle_dto: VehicleDTO,
        component_type: ComponentType,
        replacement_date: date,
    ) -> date | None:
        """Рассчитать дату следующей замены из интервала по месяцу."""
        months = ComponentIntervalUtils.get_interval_months_for_component(
            vehicle_dto, component_type,
        )
        if months is None:
            return None
        return add_months(replacement_date, months)

    @staticmethod
    def get_all_intervals(vehicle_dto: VehicleDTO) -> dict[ComponentType, int]:
        """Получить все интервалы автомобиля."""
        return {cfg.type: vehicle_dto.intervals.get(cfg.type.value, 0) for cfg in COMPONENTS_CONFIG}
