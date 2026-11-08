from datetime import date

from pydantic import BaseModel, Field, field_validator

MAX_PLATE_LENGTH = 15


def normalize_plate_number(value: str) -> str:
    """Нормализация госномера свободного формата."""
    normalized = value.strip()

    if not normalized:
        raise ValueError('Введите госномер')

    if any(ord(ch) < 32 for ch in normalized):
        raise ValueError('Госномер не может содержать управляющие символы')

    normalized = normalized.upper()

    if len(normalized) > MAX_PLATE_LENGTH:
        raise ValueError(
            f'Госномер не может быть длиннее {MAX_PLATE_LENGTH} символов'
        )

    return normalized


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
        return normalize_plate_number(v)

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Проверка, что год выпуска не позже следующего года."""
        if v > date.today().year + 1:
            raise ValueError(
                f'Год выпуска не может быть позже {date.today().year + 1}'
            )
        return v
