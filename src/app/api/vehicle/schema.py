from pydantic import BaseModel, Field

from app.common.schemas.base_vehicle import VehicleBase, VehicleIntervals


class VehicleRequest(VehicleBase, VehicleIntervals):
    """Модель запроса создания авто."""


class VehicleResponse(VehicleIntervals, VehicleBase):
    """Модель ответа с данными авто."""
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
    oil_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены масла',
    )
    transmission_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены масла АКПП',
    )
    brake_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены тормозной жидкости',
    )
    coolant_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены антифриза',
    )
    power_steering_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены жидкости ГУР',
    )
    differential_oil_km_remaining: int | None = Field(
        None,
        description='Остаток км до замены масла в редукторе',
    )


class UpdateKMRequest(BaseModel):
    """Модель обновления текущего пробега."""
    new_km: int = Field(
        ...,
        description='Новый пробег авто',
        examples=[150000],
        ge=0,
    )


class UpdateVehicleData(VehicleBase):
    """Обновить данные автомобиля."""


class VehicleUpdateIntervals(VehicleIntervals):
    """Обновление интервалов замен."""
