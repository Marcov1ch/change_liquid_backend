from datetime import date
from pydantic import Field
from app.common.schemas.base_replacement import ReplacementBase


class Replacement(ReplacementBase):
    """Модель замены компонента."""
    id: int | None = Field(
        None,
        description='ID записи',
    )
    vehicle_id: int = Field(
        ...,
        description='ID автомобиля',
    )
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
    interval_km: int = Field(
        ...,
        description='Интервал замены (км)',
        ge=0,
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей обязательной замены (для date-based компонентов)',
        examples=['2026-11-01'],
    )
    interval_months: int | None = Field(
        None,
        description='Интервал замены в месяцах',
    )
