import re

from pydantic import BaseModel, Field, field_validator


class VehicleBase(BaseModel):
    """Базовая модель авто."""
    brand: str = Field(
        ...,
        description='Марка автомобиля',
        examples=['Honda'],
        min_length=1,
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
        examples=['А123АА178', '1234AB7'],
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
        """Проверка формата госномера (РФ или РБ)."""
        allowed_letters = 'АВЕІКМНОРСТУХ'

        patterns = [
            rf'^[{allowed_letters}]\d{{3}}[{allowed_letters}]{{2}}\d{{2,3}}$',
            rf'^\d{{4}}[{allowed_letters}]{{2}}\d$',
            rf'^\d{{4}}[{allowed_letters}]{{2}}$',
        ]

        cleaned = v.replace(' ', '').replace('-', '').upper()

        if not any(re.match(p, cleaned) for p in patterns):
            raise ValueError(
                'Некорректный формат госномера. '
                'Допустимые форматы: А123АА178 (РФ) или 1234AB7 (РБ)'
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
