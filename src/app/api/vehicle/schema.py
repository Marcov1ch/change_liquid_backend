from pydantic import BaseModel, Field

from app.common.schemas.base_vehicle import VehicleBase, VehicleIntervals, Notify


class VehicleRequest(VehicleBase, VehicleIntervals, Notify):
    """Модель запроса создания авто."""


class VehicleResponse(VehicleIntervals, VehicleBase, Notify):
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


class UpdateVehicleData(VehicleBase, VehicleIntervals):
    """Обновить данные автомобиля."""
    oil_notify_enabled: bool | None = Field(None, description='Уведомлять о замене масла')
    transmission_notify_enabled: bool | None = Field(None, description='Уведомлять о замене масла АКПП')
    brake_notify_enabled: bool | None = Field(None, description='Уведомлять о замене тормозной жидкости')
    coolant_notify_enabled: bool | None = Field(None, description='Уведомлять о замене антифриза')
    power_steering_notify_enabled: bool | None = Field(None, description='Уведомлять о замене жидкости ГУР')
    differential_oil_notify_enabled: bool | None = Field(None, description='Уведомлять о замене масла в редукторе')


class VehicleUpdateIntervals(VehicleIntervals):
    """Обновление интервалов замен."""
