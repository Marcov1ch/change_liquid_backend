from pydantic import BaseModel, Field
from app.common.enums import ComponentType


class ReplacementBase(BaseModel):
    """Базовая модель замены компонента."""
    component_type: ComponentType = Field(
        ...,
        description='Тип компонента',
        examples=[ComponentType.ENGINE_OIL.value],
    )
    component_name: str = Field(
        ...,
        description='Название компонента',
        examples=['Mobil 1 5W-30'],
        min_length=1,
        max_length=100,
    )
    component_price: int | None = Field(
        None,
        description='Цена компонента в рублях',
        examples=[5000],
        ge=0,
    )
    work_price: int | None = Field(
        None,
        description='Стоимость работы в рублях',
        examples=[1500],
        ge=0,
    )
