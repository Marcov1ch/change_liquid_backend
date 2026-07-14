from enum import Enum


class ComponentType(Enum):
    """Типы отслеживаемых компонентов (жидкости, фильтры, свечи и т.д.)."""
    ENGINE_OIL = 'engine_oil'
    TRANSMISSION_OIL = "transmission_oil"
    COOLANT = "coolant"
    BRAKE_FLUID = "brake_fluid"
    POWER_STEERING_FLUID = "power_steering_fluid"
    DIFFERENTIAL_OIL = "differential_oil"


class StatusEnum(Enum):
    """Статусы по заменам."""
    OVERDUE = "overdue"
    CRITICAL = "critical"
    WARNING = "warning"
    GOOD = "good"
    UNKNOWN = "unknown"
    REPLACED = "replaced"
