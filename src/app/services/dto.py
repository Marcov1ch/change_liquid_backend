from dataclasses import dataclass
from datetime import date

from app.common.enums import BrandCar, LiquidType


@dataclass
class VehicleDTO:
    """DTO для передачи данных об авто между сервисом и handler."""
    id: int | None
    brand: BrandCar
    model: str
    plate_number: str
    year: int
    current_km: int
    is_active: bool
    oil_interval_km: int
    transmission_interval_km: int
    brake_interval_km: int
    coolant_interval_km: int
    power_steering_interval_km: int
    differential_oil_interval_km: int


@dataclass
class ReplacementDTO:
    """DTO для передачи данных о замене между сервисом и handler."""
    id: int | None
    vehicle_id: int
    liquid_type: LiquidType
    liquid_name: str
    liquid_price: int | None
    work_price: int | None
    replacement_date: date
    km_at_replacement: int
    interval_km: int
