from pydantic import BaseModel, Field


class VehicleNotify(BaseModel):
    """Настройки уведомлений по каждой жидкости."""
    oil_notify_enabled: bool = Field(
        True,
        description='Уведомления о замене масла',
    )
    transmission_notify_enabled: bool = Field(
        True,
        description='Уведомления о замене масла АКПП',
    )
    brake_notify_enabled: bool = Field(
        True,
        description='Уведомления о замене тормозной жидкости',
    )
    coolant_notify_enabled: bool = Field(
        True,
        description='Уведомления о замене антифриза',
    )
    power_steering_notify_enabled: bool = Field(
        True,
        description='Уведомления о замене жидкости ГУР',
    )
    differential_oil_notify_enabled: bool = Field(
        True,
        description='Уведомления о замене масла редуктора',
    )
