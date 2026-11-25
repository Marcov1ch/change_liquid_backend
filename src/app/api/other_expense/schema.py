from datetime import date
from pydantic import BaseModel, Field

from app.common.enums import Currency


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
    amount: float = Field(
        ...,
        description='Стоимость траты в валюте пользователя',
        examples=[500.0],
        gt=0,
    )
    currency: Currency | None = Field(
        None,
        description='Валюта ввода; по умолчанию — валюта профиля',
        examples=[Currency.EUR.value],
    )


class OtherExpenseUpdateRequest(BaseModel):
    """Частичное обновление прочей траты."""
    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
    )
    expense_date: date | None = None
    amount: float | None = Field(
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
    amount: float = Field(
        ...,
        description='Стоимость траты в валюте пользователя',
    )
