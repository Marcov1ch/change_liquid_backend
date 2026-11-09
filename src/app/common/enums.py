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
    PARKING_MONTHLY = "parking_monthly"


DATE_ONLY_COMPONENT_TYPES = frozenset({ComponentType.INSURANCE, ComponentType.PARKING_MONTHLY})
DATE_ONLY_COMPONENT_KEYS = frozenset(component.value for component in DATE_ONLY_COMPONENT_TYPES)
DATE_BASED_COMPONENT_TYPES = frozenset({ComponentType.TIRE_CHANGE}) | DATE_ONLY_COMPONENT_TYPES
DATE_BASED_COMPONENT_KEYS = frozenset(component.value for component in DATE_BASED_COMPONENT_TYPES)


class TireSeason(Enum):
    """Сезон комплекта шин."""
    SUMMER = "summer"
    WINTER = "winter"
    ALL_SEASON = "all_season"


class TireEventType(Enum):
    """Тип события по шинам в истории замен."""
    PURCHASE = "purchase"
    INSTALL = "install"


class StatusEnum(Enum):
    """Статусы по заменам."""
    OVERDUE = "overdue"
    CRITICAL = "critical"
    WARNING = "warning"
    GOOD = "good"
    UNKNOWN = "unknown"
    REPLACED = "replaced"
