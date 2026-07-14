from app.common.enums import ComponentType
from app.common.component_config import COMPONENTS_CONFIG
from app.services.dto import VehicleDTO


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
