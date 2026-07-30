from app.common.enums import ComponentType
from app.common.component_config import COMPONENTS_CONFIG
from app.services.dto import ReplacementDTO, VehicleDTO


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
    def get_all_intervals(vehicle_dto: VehicleDTO) -> dict[ComponentType, int]:
        """Получить все интервалы автомобиля."""
        return {cfg.type: vehicle_dto.intervals.get(cfg.type.value, 0) for cfg in COMPONENTS_CONFIG}
