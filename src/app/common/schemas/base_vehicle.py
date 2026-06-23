import re

from pydantic import BaseModel, Field, field_validator

from app.common.enums import BrandCar


class VehicleBase(BaseModel):
    """Базовая модель авто."""
    brand: BrandCar = Field(
        ...,
        description='Марка автомобиля',
        examples=[BrandCar.HONDA.value],
    )
    model: str = Field(
        ...,
        description='Модель автомобиля',
        examples=['CR-V'],
        min_length=1,
    )
    plate_number: str = Field(
        ...,
        description='Рег. номер',
        examples=['А123АА198'],
    )
    year: int = Field(
        ...,
        description='Год выпуска автомобиля',
        examples=[2003],
        ge=1960,
        le=2026,
    )
    current_km: int = Field(
        ...,
        description='Текущий пробег автомобиля',
        examples=[106000],
        ge=0,
    )

    @field_validator('plate_number')
    @classmethod
    def validate_plate_number(cls, v: str) -> str:
        """Проверка формата госномера."""
        allowed_letters = 'АВЕКМНОРСТУХ'

        pattern = rf'^[{allowed_letters}]\d{{3}}[{allowed_letters}]{{2}}\d{{2,3}}$'

        cleaned = v.replace(' ', '').upper()

        if not re.match(pattern, cleaned):
            raise ValueError(
                f'Некорректный формат госномера. '
                f'Разрешённые буквы: {", ".join(allowed_letters)}. '
                f'Пример: А123АА198'
            )

        return cleaned


class VehicleIntervals(BaseModel):
    """Интервалы замен жидкостей."""
    oil_interval_km: int = Field(
        7000,
        description="Интервал замены масла (км)",
        examples=[7000],
        ge=1000,
    )
    transmission_interval_km: int = Field(
        60000,
        description="Интервал замены масла АКПП (км)",
        examples=[60000],
        ge=10000,
    )
    brake_interval_km: int = Field(
        40000,
        description="Интервал замены тормозной жидкости (км)",
        examples=[40000],
        ge=10000,
    )
    coolant_interval_km: int = Field(
        60000,
        description="Интервал замены антифриза (км)",
        examples=[60000],
        ge=10000,
    )
    power_steering_interval_km: int = Field(
        40000,
        description="Интервал замены жидкости ГУРа (км)",
        examples=[40000],
        ge=10000,
    )
    differential_oil_interval_km: int = Field(
        80000,
        description="Интервал замены масла в редукторе (км)",
        examples=[80000],
        ge=10000,
    )
