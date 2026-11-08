from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.common.enums import ComponentType, DATE_BASED_COMPONENT_TYPES


def _validate_component_types(component_types: list[ComponentType]) -> list[ComponentType]:
    """Оставить только km-based компоненты без дублей."""
    if any(item in DATE_BASED_COMPONENT_TYPES for item in component_types):
        raise ValueError(
            'В ремонт можно добавлять только компоненты, отслеживаемые по пробегу'
        )
    return list(dict.fromkeys(component_types))


class RepairCreateRequest(BaseModel):
    """Запрос на создание ремонта."""
    repair_date: date = Field(
        ...,
        description='Дата ремонта',
        examples=['2024-01-15'],
    )
    km_at_repair: int = Field(
        ...,
        description='Пробег на момент ремонта',
        ge=0,
        examples=[15000],
    )
    description: str | None = Field(
        None,
        max_length=2000,
        description='Описание работ',
    )
    work_cost: int = Field(
        ...,
        ge=0,
        description='Стоимость работ',
    )
    parts_cost: int = Field(
        ...,
        ge=0,
        description='Стоимость запчастей',
    )
    component_types: list[ComponentType] = Field(
        default_factory=list,
        description='Компоненты, заменённые в рамках ремонта',
    )

    @field_validator('component_types')
    @classmethod
    def validate_component_types(cls, v: list[ComponentType]) -> list[ComponentType]:
        return _validate_component_types(v)


class RepairUpdateRequest(RepairCreateRequest):
    """Полное обновление ремонта."""


class RepairResponse(BaseModel):
    """Ответ с данными о ремонте."""
    id: int = Field(
        ...,
        description='ID ремонта',
    )
    vehicle_id: int = Field(
        ...,
        description='ID автомобиля',
    )
    repair_date: date = Field(
        ...,
        description='Дата ремонта',
    )
    km_at_repair: int = Field(
        ...,
        description='Пробег на момент ремонта',
    )
    description: str | None = Field(
        None,
        description='Описание работ',
    )
    work_cost: int = Field(
        ...,
        description='Стоимость работ',
    )
    parts_cost: int = Field(
        ...,
        description='Стоимость запчастей',
    )
    component_types: list[ComponentType] = Field(
        default_factory=list,
        description='Компоненты, заменённые в рамках ремонта',
    )
