from app.common.enums import LiquidType
from dataclasses import dataclass


@dataclass
class LiquidConfig:
    type: LiquidType
    interval_field: str
    remaining_field: str
    notify_field: str
    name: str
    name_genitive: str


LIQUIDS_CONFIG = [
    LiquidConfig(
        LiquidType.ENGINE_OIL,
        'oil_interval_km', 'oil_km_remaining',
        'oil_notify_enabled', 'Моторное масло', 'моторного масла',
    ),
    LiquidConfig(
        LiquidType.TRANSMISSION_OIL,
        'transmission_interval_km', 'transmission_km_remaining',
        'transmission_notify_enabled', 'Масло АКПП', 'масла АКПП',
    ),
    LiquidConfig(
        LiquidType.BRAKE_FLUID,
        'brake_interval_km', 'brake_km_remaining',
        'brake_notify_enabled', 'Тормозная жидкость', 'тормозной жидкости',
    ),
    LiquidConfig(
        LiquidType.COOLANT,
        'coolant_interval_km', 'coolant_km_remaining',
        'coolant_notify_enabled', 'Антифриз', 'антифриза',
    ),
    LiquidConfig(
        LiquidType.POWER_STEERING_FLUID,
        'power_steering_interval_km', 'power_steering_km_remaining',
        'power_steering_notify_enabled', 'Жидкость ГУР', 'жидкости ГУР',
    ),
    LiquidConfig(
        LiquidType.DIFFERENTIAL_OIL,
        'differential_oil_interval_km', 'differential_oil_km_remaining',
        'differential_oil_notify_enabled', 'Масло в редукторе', 'масла в редукторе',
    ),
]
