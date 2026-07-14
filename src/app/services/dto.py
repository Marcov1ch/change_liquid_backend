from dataclasses import dataclass
from datetime import date

from app.common.enums import LiquidType


@dataclass
class VehicleDTO:
    """DTO для передачи данных об авто между сервисом и handler."""
    id: int | None
    brand: str
    model: str
    brand_id: int
    model_id: int
    plate_number: str
    year: int
    current_km: int
    is_active: bool
    owner_id: int
    oil_interval_km: int
    transmission_interval_km: int
    brake_interval_km: int
    coolant_interval_km: int
    power_steering_interval_km: int
    differential_oil_interval_km: int
    oil_notify_enabled: bool = True
    transmission_notify_enabled: bool = True
    brake_notify_enabled: bool = True
    coolant_notify_enabled: bool = True
    power_steering_notify_enabled: bool = True
    differential_oil_notify_enabled: bool = True


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
