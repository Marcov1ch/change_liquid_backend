from app.common.enums import ComponentType
from dataclasses import dataclass


@dataclass
class ComponentConfig:
    type: ComponentType
    interval_field: str
    remaining_field: str
    notify_field: str
    name: str
    name_genitive: str


COMPONENTS_CONFIG = [
    ComponentConfig(
        ComponentType.ENGINE_OIL,
        'oil_interval_km', 'oil_km_remaining',
        'oil_notify_enabled', 'Моторное масло', 'моторного масла',
    ),
    ComponentConfig(
        ComponentType.TRANSMISSION_OIL,
        'transmission_interval_km', 'transmission_km_remaining',
        'transmission_notify_enabled', 'Масло АКПП', 'масла АКПП',
    ),
    ComponentConfig(
        ComponentType.BRAKE_FLUID,
        'brake_interval_km', 'brake_km_remaining',
        'brake_notify_enabled', 'Тормозная жидкость', 'тормозной жидкости',
    ),
    ComponentConfig(
        ComponentType.COOLANT,
        'coolant_interval_km', 'coolant_km_remaining',
        'coolant_notify_enabled', 'Антифриз', 'антифриза',
    ),
    ComponentConfig(
        ComponentType.POWER_STEERING_FLUID,
        'power_steering_interval_km', 'power_steering_km_remaining',
        'power_steering_notify_enabled', 'Жидкость ГУР', 'жидкости ГУР',
    ),
    ComponentConfig(
        ComponentType.DIFFERENTIAL_OIL,
        'differential_oil_interval_km', 'differential_oil_km_remaining',
        'differential_oil_notify_enabled', 'Масло в редукторе', 'масла в редукторе',
    ),
]
