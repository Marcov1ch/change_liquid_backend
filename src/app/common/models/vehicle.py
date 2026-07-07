from pydantic import Field

from app.common.schemas.base_vehicle import VehicleBase, VehicleIntervals


class Vehicle(VehicleBase, VehicleIntervals):
    """Модель авто."""
    id: int | None = Field(
        None,
        description='id автомобиля',
    )
    brand_id: int = Field(
        ...,
        description='id марки из таблицы brands',
    )
    model_id: int = Field(
        ...,
        description='id модели из таблицы models',
    )
    owner_id: int | None = Field(
        None,
        description='id владельца',
    )
    is_active: bool = Field(
        True,
        description='Флаг активного автомобиля',
        examples=[True],
    )
