from app.common.enums import LiquidType
from dataclasses import dataclass


@dataclass
class LiquidConfig:
    type: LiquidType
    interval_field: str
    remaining_field: str


LIQUIDS_CONFIG = [
    LiquidConfig(LiquidType.ENGINE_OIL, 'oil_interval_km', 'oil_km_remaining'),
    LiquidConfig(LiquidType.TRANSMISSION_OIL, 'transmission_interval_km', 'transmission_km_remaining'),
    LiquidConfig(LiquidType.BRAKE_FLUID, 'brake_interval_km', 'brake_km_remaining'),
    LiquidConfig(LiquidType.COOLANT, 'coolant_interval_km', 'coolant_km_remaining'),
    LiquidConfig(LiquidType.POWER_STEERING_FLUID, 'power_steering_interval_km', 'power_steering_km_remaining'),
    LiquidConfig(LiquidType.DIFFERENTIAL_OIL, 'differential_oil_interval_km', 'differential_oil_km_remaining'),
]
