from datetime import date

from pydantic import BaseModel, Field

from app.common.enums import ComponentType, StatusEnum


class ShareLinkResponse(BaseModel):
    """Состояние публичной ссылки на авто."""
    enabled: bool = Field(
        ...,
        description='Включён ли публичный доступ',
    )
    token: str | None = Field(
        None,
        description='Публичный токен',
    )
    share_url: str | None = Field(
        None,
        description='Ссылка для QR-кода',
    )
    register_url: str = Field(
        ...,
        description='Ссылка на регистрацию',
    )


class PublicReplacementResponse(BaseModel):
    """Запись о замене в публичном профиле."""
    id: int = Field(
        ...,
        description='ID записи о замене',
    )
    component_type: ComponentType = Field(
        ...,
        description='Тип компонента',
    )
    component_name: str = Field(
        ...,
        description='Название компонента',
    )
    component_price: int | None = Field(
        None,
        description='Цена компонента',
    )
    work_price: int | None = Field(
        None,
        description='Стоимость работы',
    )
    replacement_date: date = Field(
        ...,
        description='Дата замены',
    )
    km_at_replacement: int = Field(
        ...,
        description='Пробег при замене',
    )
    interval_km: int = Field(
        ...,
        description='Интервал замены',
    )
    next_replacement_km: int | None = Field(
        None,
        description='Следующая замена по пробегу',
    )
    km_remaining: int | None = Field(
        None,
        description='Остаток км до замены',
    )
    km_traveled: int | None = Field(
        None,
        description='Пройдено километров с момента замены (для шин)',
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей замены',
    )
    days_remaining: int | None = Field(
        None,
        description='Остаток дней до замены',
    )
    status: StatusEnum = Field(
        ...,
        description='Статус замены',
    )


class PublicVehicleResponse(BaseModel):
    """Публичный профиль авто с историей замен."""
    brand: str = Field(
        ...,
        description='Марка автомобиля',
    )
    model: str = Field(
        ...,
        description='Модель автомобиля',
    )
    plate_number: str = Field(
        ...,
        description='Рег. номер',
    )
    year: int = Field(
        ...,
        description='Год выпуска',
    )
    current_km: int = Field(
        ...,
        description='Текущий пробег',
    )
    vehicle_status: str = Field(
        ...,
        description='Общий статус авто',
    )
    replacements: list[PublicReplacementResponse] = Field(
        default_factory=list,
        description='История замен',
    )
    register_url: str = Field(
        ...,
        description='Ссылка на регистрацию',
    )
