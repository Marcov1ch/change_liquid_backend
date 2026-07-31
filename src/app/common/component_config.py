from app.common.enums import ComponentType
from dataclasses import dataclass


@dataclass
class ComponentConfig:
    type: ComponentType
    interval_field: str
    notify_field: str
    name: str
    name_genitive: str
    example: str
    default_interval: int


COMPONENTS_CONFIG = [
    ComponentConfig(
        ComponentType.ENGINE_OIL,
        'oil_interval_km',
        'oil_notify_enabled',
        'Моторное масло',
        'моторного масла',
        'Mobil 1 5W-30',
        7000,
    ),
    ComponentConfig(
        ComponentType.TRANSMISSION_OIL,
        'transmission_interval_km',
        'transmission_notify_enabled',
        'Масло АКПП',
        'масла АКПП',
        'Toyota ATF WS',
        60000,
    ),
    ComponentConfig(
        ComponentType.BRAKE_FLUID,
        'brake_interval_km',
        'brake_notify_enabled',
        'Тормозная жидкость',
        'тормозной жидкости',
        'DOT 4',
        40000,
    ),
    ComponentConfig(
        ComponentType.COOLANT,
        'coolant_interval_km',
        'coolant_notify_enabled',
        'Антифриз',
        'антифриза',
        'CoolStream G12',
        60000,
    ),
    ComponentConfig(
        ComponentType.POWER_STEERING_FLUID,
        'power_steering_interval_km',
        'power_steering_notify_enabled',
        'Жидкость ГУР',
        'жидкости ГУР',
        'Pentosin CHF 11S',
        40000,
    ),
    ComponentConfig(
        ComponentType.DIFFERENTIAL_OIL,
        'differential_oil_interval_km',
        'differential_oil_notify_enabled',
        'Масло в редукторе',
        'масла в редукторе',
        '75W-90 GL-5',
        50000,
    ),
    ComponentConfig(
        ComponentType.CABIN_FILTER,
        'cabin_filter_interval_km',
        'cabin_filter_notify_enabled',
        'Фильтр салона',
        'фильтра салона',
        'MANN CUK 2643',
        15000,
    ),
    ComponentConfig(
        ComponentType.SPARK_PLUGS,
        'spark_plugs_interval_km',
        'spark_plugs_notify_enabled',
        'Свечи зажигания',
        'свечей зажигания',
        'NGK BKR6E',
        45000,
    ),
    ComponentConfig(
        ComponentType.AIR_FILTER,
        'air_filter_interval_km',
        'air_filter_notify_enabled',
        'Воздушный фильтр',
        'воздушного фильтра',
        'MANN C 36106',
        10000,
    ),
]
