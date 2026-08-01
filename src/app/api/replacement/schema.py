from datetime import date
from pydantic import BaseModel, Field

from app.common.schemas.base_replacement import ReplacementBase
from app.common.enums import StatusEnum


class ReplacementCreateRequest(ReplacementBase):
    """Запрос на создание замены."""
    replacement_date: date = Field(
        ...,
        description='Дата замены',
        examples=['2024-01-15'],
    )
    km_at_replacement: int = Field(
        ...,
        description='Пробег на момент замены',
        examples=[15000],
        ge=0,
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей обязательной замены (для шин)',
        examples=['2026-11-01'],
    )


class ReplacementResponse(ReplacementBase):
    """Ответ с данными о замене."""
    id: int = Field(
        ...,
        description='ID записи о замене',
    )
    vehicle_id: int = Field(
        ...,
        description='ID автомобиля',
    )
    replacement_date: date = Field(
        ...,
        description='Дата замены',
    )
    km_at_replacement: int = Field(
        ...,
        description='Пробег при замене',
    )
    interval_km: int = Field(
        ...,
        description='Интервал замены (из настроек авто)',
    )
    next_replacement_km: int = Field(
        ...,
        description='Следующая замена при пробеге',
    )
    km_remaining: int = Field(
        ...,
        description='Остаток в километрах до замены',
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей обязательной замены',
    )
    days_remaining: int | None = Field(
        None,
        description='Остаток дней до замены',
    )
    status: StatusEnum = Field(
        ...,
        description='Статус замены',
    )
    status_message: str = Field(
        ...,
        description='Сообщение статуса',
    )


class UpdateReplacementRequest(BaseModel):
    """Обновление записи о замене (тип компонента не изменяем)."""
    component_name: str | None = Field(None, min_length=1, max_length=100)
    component_price: int | None = Field(None, ge=0)
    work_price: int | None = Field(None, ge=0)
    replacement_date: date | None = None
    km_at_replacement: int | None = Field(None, ge=0)
    next_change_date: date | None = None


class ReplacementsBulkRequest(BaseModel):
    """Массовое создание замен."""
    replacements: list[ReplacementCreateRequest] = Field(
        ...,
        description='Список замен',
        min_length=1,
        max_length=10,
    )
