from datetime import date

from pydantic import BaseModel, Field


class FuelRecordCreateRequest(BaseModel):
    """Запрос на создание заправки."""
    fuel_date: date = Field(
        ...,
        description='Дата заправки',
        examples=['2026-05-10'],
    )
    km_at_fuel: int = Field(
        ...,
        description='Пробег на момент заправки',
        ge=0,
        examples=[120000],
    )
    liters: float = Field(
        ...,
        description='Объём топлива в литрах',
        gt=0,
        examples=[35.5],
    )
    total_cost: int = Field(
        ...,
        description='Стоимость заправки в рублях',
        ge=0,
        examples=[2500],
    )


class FuelRecordUpdateRequest(BaseModel):
    """Частичное обновление заправки."""
    fuel_date: date | None = None
    km_at_fuel: int | None = Field(None, ge=0)
    liters: float | None = Field(None, gt=0)
    total_cost: int | None = Field(None, ge=0)


class FuelRecordResponse(BaseModel):
    """Ответ с данными о заправке."""
    id: int = Field(
        ...,
        description='ID заправки',
    )
    vehicle_id: int = Field(
        ...,
        description='ID автомобиля',
    )
    fuel_date: date = Field(
        ...,
        description='Дата заправки',
    )
    km_at_fuel: int = Field(
        ...,
        description='Пробег на момент заправки',
    )
    liters: float = Field(
        ...,
        description='Объём топлива в литрах',
    )
    total_cost: int = Field(
        ...,
        description='Стоимость заправки в рублях',
    )
    consumption_l_per_100km: float | None = Field(
        None,
        description='Расход топлива между соседними заправками, л/100 км',
    )
