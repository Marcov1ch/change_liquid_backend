from pydantic import BaseModel, Field, field_validator

from app.common.schemas.base_vehicle import VehicleBase, normalize_plate_number


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
    def validate_plate_number(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_plate_number(v)  # type: ignore[no-any-return]


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
