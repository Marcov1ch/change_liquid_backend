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
        ge=1000,
    )
