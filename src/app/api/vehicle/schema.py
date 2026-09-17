from datetime import date

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.common.schemas.base_vehicle import VehicleBase, normalize_plate_number


class RimSize(BaseModel):
    """Позиция диска автомобиля."""
    diameter: int | None = Field(None, description='Диаметр диска в дюймах', examples=[16], ge=1)
    pcd: str | None = Field(None, description='Сверловка (PCD)', examples=['5x114.3'], max_length=30)
    et_from: int | None = Field(None, description='Вылет диска, от', examples=[45], ge=-100, le=200)
    et_to: int | None = Field(None, description='Вылет диска, до', examples=[50], ge=-100, le=200)
    width_from: float | None = Field(None, description='Ширина диска в дюймах, от', examples=[6], ge=1, le=30)
    width_to: float | None = Field(None, description='Ширина диска в дюймах, до', examples=[6.5], ge=1, le=30)

    @field_validator('et_to')
    @classmethod
    def validate_et_range(cls, v: int | None, info: ValidationInfo) -> int | None:
        if v is not None and info.data.get('et_from') is not None and v < info.data['et_from']:
            raise ValueError('Верхняя граница вылета не может быть меньше нижней')
        return v

    @field_validator('width_to')
    @classmethod
    def validate_width_range(cls, v: float | None, info: ValidationInfo) -> float | None:
        if v is not None and info.data.get('width_from') is not None and v < info.data['width_from']:
            raise ValueError('Верхняя граница ширины не может быть меньше нижней')
        return v


class TireSize(BaseModel):
    """Позиция шины автомобиля."""
    size: str = Field(..., description='Размер шины', examples=['215/65 R16'], min_length=1, max_length=30)
    label: str | None = Field(
        None,
        description='Подпись (сезон, бренд и т.п.)',
        examples=['лето'],
        max_length=50,
    )


class UpdateVehicleSizes(BaseModel):
    """Обновление списков дисков и шин (полная замена)."""
    rims: list[RimSize] = Field(
        default_factory=list,
        description='Список допустимых дисков',
    )
    tires: list[TireSize] = Field(
        default_factory=list,
        description='Список допустимых размеров шин',
    )


class VehicleCreateRequest(VehicleBase):
    """Модель запроса создания авто."""
    intervals: dict[str, int] = Field(
        default_factory=dict,
        description='Интервалы замен по компонентам (км)',
        examples=[{"engine_oil": 7000, "transmission_oil": 60000}],
    )
    notify_flags: dict[str, bool] = Field(
        default_factory=dict,
        description='Настройки уведомлений по компонентам',
        examples=[{"engine_oil": True, "transmission_oil": True}],
    )
    interval_months: dict[str, int | None] = Field(
        default_factory=dict,
        description='Интервалы замен по компонентам (месяцы)',
        examples=[{"engine_oil": 12, "brake_fluid": 24}],
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
    interval_months: dict[str, int | None] = Field(
        default_factory=dict,
        description='Интервалы замен по компонентам (месяцы)',
    )
    km_remaining: dict[str, int | None] = Field(
        default_factory=dict,
        description='Остаток км до замены по каждому компоненту',
    )
    rims: list[RimSize] = Field(
        default_factory=list,
        description='Список допустимых дисков',
    )
    tires: list[TireSize] = Field(
        default_factory=list,
        description='Список допустимых размеров шин',
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
    year: int | None = Field(None, ge=1960)
    current_km: int | None = Field(None, ge=0)
    intervals: dict[str, int] | None = Field(
        None,
        description='Интервалы замен для обновления',
    )
    notify_flags: dict[str, bool] | None = Field(
        None,
        description='Настройки уведомлений для обновления',
    )
    interval_months: dict[str, int | None] | None = Field(
        None,
        description='Интервалы замен по компонентам (месяцы) для обновления',
    )

    @field_validator('plate_number')
    @classmethod
    def validate_plate_number(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_plate_number(v)  # type: ignore[no-any-return]

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int | None) -> int | None:
        if v is not None and v > date.today().year + 1:
            raise ValueError(
                f'Год выпуска не может быть позже {date.today().year + 1}'
            )
        return v


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
