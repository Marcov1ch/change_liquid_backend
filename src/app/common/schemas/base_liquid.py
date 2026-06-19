from pydantic import BaseModel, Field
from app.common.enums import LiquidType


class LiquidBase(BaseModel):
    """Базовая модель жидкости."""
    liquid_type: LiquidType = Field(
        ...,
        description='Тип жидкости',
        examples=[LiquidType.ENGINE_OIL.value],
    )
    liquid_name: str = Field(
        ...,
        description='Название жидкости/масла',
        examples=['Mobil 1 5W-30'],
        min_length=1,
        max_length=100,
    )
    liquid_price: int | None = Field(
        None,
        description='Цена жидкости в рублях',
        examples=[5000],
        ge=0,
    )
    work_price: int | None = Field(
        None,
        description='Стоимость работы в рублях',
        examples=[1500],
        ge=0,
    )
