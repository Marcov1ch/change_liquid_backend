import re

from pydantic import BaseModel, Field, field_validator

from app.common.schemas.base_vehicle import VehicleBase


class VehicleCreateRequest(VehicleBase):
    """Модель запроса создания авто."""
    intervals: dict[str, int] = Field(
        default_factory=dict,
        description='Интервалы замен по компонентам',
        examples=[{"engine_oil": 7000, "transmission_oil": 60000}],
    )
    notify_flags: dict[str, bool] = Field(
        default_factory=dict,
        description='Настройки уведомлений по компонентам',
        examples=[{"engine_oil": True, "transmission_oil": True}],
    )


class VehicleResponse(VehicleBase):
    """Ответ с данными авто."""
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
    intervals: dict[str, int] = Field(
        default_factory=dict,
        description='Интервалы замен по компонентам',
    )
    notify_flags: dict[str, bool] = Field(
        default_factory=dict,
        description='Настройки уведомлений',
    )
    km_remaining: dict[str, int | None] = Field(
        default_factory=dict,
        description='Остаток км до замены по каждому компоненту',
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
    intervals: dict[str, int] | None = Field(
        None,
        description='Интервалы замен для обновления',
    )
    notify_flags: dict[str, bool] | None = Field(
        None,
        description='Настройки уведомлений для обновления',
    )

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


class VehicleUpdateIntervals(BaseModel):
    """Обновление интервалов замен (PATCH — все поля опциональны)."""
    intervals: dict[str, int] | None = Field(
        None,
        description='Интервалы замен для обновления',
    )


class UpdateVehicleNotify(BaseModel):
    """Обновление настроек уведомлений (PATCH — все поля опциональны)."""
    notify_flags: dict[str, bool] | None = Field(
        None,
        description='Настройки уведомлений для обновления',
    )
