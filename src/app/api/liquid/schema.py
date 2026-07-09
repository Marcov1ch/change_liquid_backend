from datetime import date
from pydantic import BaseModel, Field

from app.common.schemas.base_liquid import LiquidBase
from app.common.enums import LiquidType


class LiquidReplacementRequest(LiquidBase):
    """Запрос на создание замены жидкости."""
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


class LiquidReplacementResponse(LiquidBase):
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
    status: str = Field(
        ...,
        description='Статус замены',
    )
    status_message: str = Field(
        ...,
        description='Сообщение статуса',
    )


class UpdateLiquidReplacementRequest(LiquidBase):
    """Обновление записи о замене."""
    liquid_type: LiquidType | None = None  # type: ignore[assignment]
    liquid_name: str | None = None  # type: ignore[assignment]
    replacement_date: date | None = None
    km_at_replacement: int | None = Field(None, ge=0)


class ReplacementsRequest(BaseModel):
    """Массовое создание замен."""
    replacements: list[LiquidReplacementRequest] = Field(
        ...,
        description='Список замен жидкостей',
        min_length=1,
        max_length=10,
    )
