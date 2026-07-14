from dataclasses import dataclass, field
from datetime import date

from app.common.enums import ComponentType


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
    intervals: dict[str, int] = field(default_factory=dict)
    notify_flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class ReplacementDTO:
    """DTO для передачи данных о замене."""
    id: int | None
    vehicle_id: int
    component_type: ComponentType
    component_name: str
    component_price: int | None
    work_price: int | None
    replacement_date: date
    km_at_replacement: int
    interval_km: int
