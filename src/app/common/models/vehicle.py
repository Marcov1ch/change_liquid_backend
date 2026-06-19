from pydantic import Field

from app.common.schemas.base_vehicle import VehicleBase, VehicleIntervals


class Vehicle(VehicleBase, VehicleIntervals):
    """Модель авто."""
    id: int | None = Field(
        None,
        description='id автомобиля',
    )
    is_active: bool = Field(
        True,
        description='Флаг активного автомобиля',
        examples=[True],
    )
