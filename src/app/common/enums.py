from enum import Enum


class ComponentType(Enum):
    """Типы отслеживаемых компонентов (жидкости, фильтры, свечи и т.д.)."""
    ENGINE_OIL = 'engine_oil'
    TRANSMISSION_OIL = "transmission_oil"
    COOLANT = "coolant"
    BRAKE_FLUID = "brake_fluid"
    POWER_STEERING_FLUID = "power_steering_fluid"
    DIFFERENTIAL_OIL = "differential_oil"
    CABIN_FILTER = "cabin_filter"
    SPARK_PLUGS = "spark_plugs"
    AIR_FILTER = "air_filter"
    FUEL_FILTER = "fuel_filter"
    TIRE_CHANGE = "tire_change"
    INSURANCE = "insurance"


DATE_BASED_COMPONENT_TYPES = frozenset({ComponentType.TIRE_CHANGE, ComponentType.INSURANCE})
DATE_BASED_COMPONENT_KEYS = frozenset(component.value for component in DATE_BASED_COMPONENT_TYPES)


class StatusEnum(Enum):
    """Статусы по заменам."""
    OVERDUE = "overdue"
    CRITICAL = "critical"
    WARNING = "warning"
    GOOD = "good"
    UNKNOWN = "unknown"
    REPLACED = "replaced"
