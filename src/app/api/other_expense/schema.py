from datetime import date
from pydantic import BaseModel, Field


class OtherExpenseCreateRequest(BaseModel):
    """Запрос на создание прочей траты."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description='Название траты',
        examples=['Штраф', 'Мойка', 'Парковка'],
    )
    expense_date: date = Field(
        ...,
        description='Дата траты',
        examples=['2024-01-15'],
    )
    amount: int = Field(
        ...,
        description='Стоимость траты в рублях',
        examples=[500],
        gt=0,
    )


class OtherExpenseUpdateRequest(BaseModel):
    """Частичное обновление прочей траты."""
    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
    )
    expense_date: date | None = None
    amount: int | None = Field(
        None,
        gt=0,
    )


class OtherExpenseResponse(BaseModel):
    """Ответ с данными о прочей трате."""
    id: int = Field(
        ...,
        description='ID записи о трате',
    )
    vehicle_id: int = Field(
        ...,
        description='ID автомобиля',
    )
    name: str = Field(
        ...,
        description='Название траты',
    )
    expense_date: date = Field(
        ...,
        description='Дата траты',
    )
    amount: int = Field(
        ...,
        description='Стоимость траты в рублях',
    )
