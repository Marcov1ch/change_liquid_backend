import re

from pydantic import BaseModel, Field, field_validator

from app.common.schemas.base_vehicle import VehicleBase, VehicleIntervals
from app.common.schemas.vehicle_notify import VehicleNotify


class VehicleRequest(VehicleBase, VehicleIntervals, VehicleNotify):
    """Модель запроса создания авто."""


class VehicleResponse(VehicleIntervals, VehicleBase, VehicleNotify):
    """Модель ответа с данными авто."""
    id: int = Field(
        ...,
        description='id автомобиля',
    )
    is_active: bool = Field(
        True,
        description='Активен ли автомобиль',
    )
    vehicle_status: str = Field(
        ...,
        description='Статус авто по заменам',
    )
    oil_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены масла',
    )
    transmission_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены масла АКПП',
    )
    brake_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены тормозной жидкости',
    )
    coolant_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены антифриза',
    )
    power_steering_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены жидкости ГУР',
    )
    differential_oil_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены масла в редукторе',
    )


class UpdateKMRequest(BaseModel):
    """Модель обновления текущего пробега."""
    new_km: int = Field(
        ...,
        description='Новый пробег авто',
        examples=[150000],
        ge=0,
    )


class UpdateVehicleData(BaseModel):
    """Обновить данные автомобиля (PATCH — все поля опциональны)."""
    brand: str | None = None
    model: str | None = None
    plate_number: str | None = None
    year: int | None = Field(None, ge=1960, le=2026)
    current_km: int | None = Field(None, ge=0)
    oil_interval_km: int | None = Field(None, ge=1000)
    transmission_interval_km: int | None = Field(None, ge=10000)
    brake_interval_km: int | None = Field(None, ge=10000)
    coolant_interval_km: int | None = Field(None, ge=10000)
    power_steering_interval_km: int | None = Field(None, ge=10000)
    differential_oil_interval_km: int | None = Field(None, ge=10000)
    oil_notify_enabled: bool | None = None
    transmission_notify_enabled: bool | None = None
    brake_notify_enabled: bool | None = None
    coolant_notify_enabled: bool | None = None
    power_steering_notify_enabled: bool | None = None
    differential_oil_notify_enabled: bool | None = None

    @field_validator('plate_number')
    @classmethod
    def validate_plate_number(cls, v: str) -> str:
        if v is None:
            return v
        allowed_letters = 'АВЕІКМНОРСТУХ'
        patterns = [
            rf'^[{allowed_letters}]\d{{3}}[{allowed_letters}]{{2}}\d{{2,3}}$',
            rf'^\d{{4}}[{allowed_letters}]{{2}}\d$',
            rf'^\d{{4}}[{allowed_letters}]{{2}}$',
        ]
        cleaned = v.replace(' ', '').replace('-', '').upper()
        if not any(re.match(p, cleaned) for p in patterns):
            raise ValueError(
                'Некорректный формат госномера. '
                'Допустимые форматы: А123АА178 (РФ) или 1234AB7 (РБ)'
            )
        return cleaned


class UpdateVehicleNotify(BaseModel):
    """Обновление настроек уведомлений (PATCH — все поля опциональны)."""
    oil_notify_enabled: bool | None = None
    transmission_notify_enabled: bool | None = None
    brake_notify_enabled: bool | None = None
    coolant_notify_enabled: bool | None = None
    power_steering_notify_enabled: bool | None = None
    differential_oil_notify_enabled: bool | None = None


class VehicleUpdateIntervals(BaseModel):
    """Обновление интервалов замен (PATCH — все поля опциональны)."""
    oil_interval_km: int | None = Field(None, ge=1000)
    transmission_interval_km: int | None = Field(None, ge=10000)
    brake_interval_km: int | None = Field(None, ge=10000)
    coolant_interval_km: int | None = Field(None, ge=10000)
    power_steering_interval_km: int | None = Field(None, ge=10000)
    differential_oil_interval_km: int | None = Field(None, ge=10000)
