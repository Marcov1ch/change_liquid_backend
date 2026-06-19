from app.common.enums import LiquidType
from app.common.models.vehicle import Vehicle


class IntervalUtils:
    """Утилиты для работы с интервалами замен."""

    @staticmethod
    def get_interval_for_liquid(
        vehicle: Vehicle,
        liquid_type: LiquidType,
    ) -> int:
        """Получить интервал замены для жидкости из настроек автомобиля."""
        intervals = {
            LiquidType.ENGINE_OIL: vehicle.oil_interval_km,
            LiquidType.TRANSMISSION_OIL: vehicle.transmission_interval_km,
            LiquidType.BRAKE_FLUID: vehicle.brake_interval_km,
            LiquidType.COOLANT: vehicle.coolant_interval_km,
            LiquidType.POWER_STEERING_FLUID: vehicle.power_steering_interval_km,
            LiquidType.DIFFERENTIAL_OIL: vehicle.differential_oil_interval_km,
        }
        return intervals[liquid_type]  # type: ignore[no-any-return]

    @staticmethod
    def get_all_intervals(vehicle: Vehicle) -> dict[LiquidType, int]:
        """Получить все интервалы автомобиля."""
        return {
            LiquidType.ENGINE_OIL: vehicle.oil_interval_km,
            LiquidType.TRANSMISSION_OIL: vehicle.transmission_interval_km,
            LiquidType.BRAKE_FLUID: vehicle.brake_interval_km,
            LiquidType.COOLANT: vehicle.coolant_interval_km,
            LiquidType.POWER_STEERING_FLUID: vehicle.power_steering_interval_km,
            LiquidType.DIFFERENTIAL_OIL: vehicle.differential_oil_interval_km,
        }
