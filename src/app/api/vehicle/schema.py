import re

from pydantic import BaseModel, Field, field_validator

from app.common.schemas.base_vehicle import VehicleBase, VehicleIntervals, Notify


class VehicleRequest(VehicleBase, VehicleIntervals, Notify):
    """Модель запроса создания авто."""


class VehicleResponse(VehicleIntervals, VehicleBase, Notify):
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
    """Обновить данные автомобиля."""
    brand: str | None = Field(None, min_length=1, description='Марка автомобиля')
    model: str | None = Field(None, min_length=1, description='Модель автомобиля')
    plate_number: str | None = Field(None, description='Рег. номер')
    year: int | None = Field(None, ge=1960, le=2026, description='Год выпуска')
    current_km: int | None = Field(None, ge=0, description='Текущий пробег')
    oil_interval_km: int | None = Field(None, ge=1000, description="Интервал замены масла (км)")
    transmission_interval_km: int | None = Field(
        None, ge=10000, description="Интервал замены масла АКПП (км)")
    brake_interval_km: int | None = Field(
        None, ge=10000, description="Интервал замены тормозной жидкости (км)")
    coolant_interval_km: int | None = Field(
        None, ge=10000, description="Интервал замены антифриза (км)")
    power_steering_interval_km: int | None = Field(
        None, ge=10000, description="Интервал замены жидкости ГУРа (км)")
    differential_oil_interval_km: int | None = Field(
        None, ge=10000, description="Интервал замены масла в редукторе (км)")
    oil_notify_enabled: bool | None = Field(None, description='Уведомлять о замене масла')
    transmission_notify_enabled: bool | None = Field(None, description='Уведомлять о замене масла АКПП')
    brake_notify_enabled: bool | None = Field(None, description='Уведомлять о замене торм. жидкости')
    coolant_notify_enabled: bool | None = Field(None, description='Уведомлять о замене антифриза')
    power_steering_notify_enabled: bool | None = Field(None, description='Уведомлять о замене жидкости ГУР')
    differential_oil_notify_enabled: bool | None = Field(
        None, description='Уведомлять о замене масла в редукторе')

    @field_validator('plate_number')
    @classmethod
    def validate_plate_number(cls, v: str | None) -> str | None:
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
                'Допустимые форматы: А123АА178 (РФ) или 1234AB7 (РБ)')
        return cleaned


class VehicleUpdateIntervals(VehicleIntervals):
    """Обновление интервалов замен."""
