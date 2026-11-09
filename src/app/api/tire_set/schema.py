from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.api.replacement.schema import ReplacementResponse
from app.common.enums import TireSeason


class TireSetCreateRequest(BaseModel):
    """Запрос на создание комплекта шин."""
    name: str = Field(
        ...,
        description='Название комплекта',
        examples=['Зимние Michelin'],
        min_length=1,
        max_length=100,
    )
    season: TireSeason = Field(
        TireSeason.ALL_SEASON,
        description='Сезон комплекта',
        examples=[TireSeason.WINTER.value],
    )
    purchase_date: date | None = Field(
        None,
        description='Дата покупки комплекта',
        examples=['2026-10-15'],
    )
    purchase_price: int | None = Field(
        None,
        description='Стоимость покупки комплекта в рублях',
        examples=[30000],
        ge=0,
    )
    install_now: bool = Field(
        False,
        description='Установить комплект сразу после добавления',
    )
    work_price: int | None = Field(
        None,
        description='Стоимость работ по установке в рублях',
        examples=[1500],
        ge=0,
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей смены шин (напоминание за 5 дней)',
        examples=['2027-04-01'],
    )

    @field_validator('name')
    @classmethod
    def validate_no_control_chars(cls, value: str) -> str:
        if any(ord(ch) < 32 for ch in value):
            raise ValueError('Название комплекта не может содержать управляющие символы')
        return value


class TireSetUpdateRequest(BaseModel):
    """Обновление комплекта шин (все поля опциональны)."""
    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
    )
    season: TireSeason | None = None
    purchase_date: date | None = None
    purchase_price: int | None = Field(
        None,
        ge=0,
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей смены шин (только для установленного комплекта)',
    )

    @field_validator('name')
    @classmethod
    def validate_no_control_chars(cls, value: str | None) -> str | None:
        if value is not None and any(ord(ch) < 32 for ch in value):
            raise ValueError('Название комплекта не может содержать управляющие символы')
        return value


class TireSetResponse(BaseModel):
    """Комплект шин."""
    id: int = Field(..., description='ID комплекта')
    vehicle_id: int = Field(..., description='ID автомобиля')
    name: str = Field(..., description='Название комплекта')
    season: TireSeason = Field(..., description='Сезон комплекта')
    purchase_date: date | None = Field(None, description='Дата покупки')
    purchase_price: int | None = Field(None, description='Стоимость покупки')
    accumulated_km: int = Field(..., description='Пробег за завершённые сезоны')
    installed_km: int | None = Field(None, description='Пробег установки текущего сезона')
    installed_date: date | None = Field(None, description='Дата установки текущего сезона')
    is_installed: bool = Field(..., description='Установлен ли комплект сейчас')
    next_change_date: date | None = Field(
        None,
        description='Дата следующей смены шин',
    )
    status: str | None = Field(
        None,
        description='Статус установленного комплекта по дате',
    )
    days_remaining: int | None = Field(
        None,
        description='Остаток дней до следующей смены',
    )
    total_km: int = Field(..., description='Суммарный пробег комплекта')
    created_at: datetime | None = Field(None, description='Дата создания записи')


class TireInstallRequest(BaseModel):
    """Запрос на переключение комплекта шин."""
    switch_date: date | None = Field(
        None,
        description='Дата переключения (по умолчанию сегодня)',
        examples=['2026-11-09'],
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей смены шин',
        examples=['2027-04-01'],
    )
    work_price: int | None = Field(
        None,
        description='Стоимость работ по установке шин в рублях',
        examples=[1500],
        ge=0,
    )


class TireInstallResponse(BaseModel):
    """Результат переключения комплекта шин."""
    tire_set: TireSetResponse = Field(..., description='Установленный комплект')
    replacement: ReplacementResponse = Field(..., description='Созданная запись установки')
