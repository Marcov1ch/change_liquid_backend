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
    component_price: float | None = Field(
        None,
        description='Цена компонента в валюте владельца',
    )
    work_price: float | None = Field(
        None,
        description='Стоимость работы в валюте владельца',
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
    tire_set_id: int | None = Field(
        None,
        description='ID комплекта шин, к которому относится запись',
    )
    tire_event_type: str | None = Field(
        None,
        description='Тип события по шинам: purchase или install',
    )


class PublicTireSetResponse(BaseModel):
    """Комплект шин в публичном профиле."""
    id: int = Field(
        ...,
        description='ID комплекта',
    )
    name: str = Field(
        ...,
        description='Название комплекта',
    )
    season: str = Field(
        ...,
        description='Сезон комплекта',
    )
    purchase_date: date | None = Field(
        None,
        description='Дата покупки',
    )
    purchase_price: float | None = Field(
        None,
        description='Стоимость покупки в валюте владельца',
    )
    is_installed: bool = Field(
        ...,
        description='Установлен ли комплект сейчас',
    )
    installed_date: date | None = Field(
        None,
        description='Дата установки текущего сезона',
    )
    next_change_date: date | None = Field(
        None,
        description='Дата следующей смены шин',
    )
    status: str | None = Field(
        None,
        description='Статус установленного комплекта по дате',
    )
    days_remaining: int | None = Field(
        None,
        description='Остаток дней до следующей смены',
    )
    total_km: int = Field(
        ...,
        description='Суммарный пробег комплекта',
    )


class PublicOtherExpenseResponse(BaseModel):
    """Прочая трата в публичном профиле."""
    id: int = Field(
        ...,
        description='ID записи о трате',
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
        description='Стоимость траты в валюте владельца',
    )


class PublicRepairResponse(BaseModel):
    """Ремонт в публичном профиле."""
    id: int = Field(
        ...,
        description='ID ремонта',
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
    work_cost: float = Field(
        ...,
        description='Стоимость работ в валюте владельца',
    )
    parts_cost: float = Field(
        ...,
        description='Стоимость запчастей в валюте владельца',
    )
    component_types: list[ComponentType] = Field(
        default_factory=list,
        description='Компоненты, заменённые в рамках ремонта',
    )


class PublicFuelRecordResponse(BaseModel):
    """Заправка в публичном профиле."""
    id: int = Field(
        ...,
        description='ID заправки',
    )
    fuel_date: date = Field(
        ...,
        description='Дата заправки',
    )
    km_at_fuel: int = Field(
        ...,
        description='Пробег на момент заправки',
    )
    liters: float = Field(
        ...,
        description='Объём топлива в литрах',
    )
    total_cost: float = Field(
        ...,
        description='Стоимость заправки в валюте владельца',
    )
    consumption_l_per_100km: float | None = Field(
        None,
        description='Расход топлива между соседними заправками, л/100 км',
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
    currency: str = Field(
        'RUB',
        description='Валюта владельца',
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
    tire_sets: list[PublicTireSetResponse] = Field(
        default_factory=list,
        description='Комплекты шин',
    )
    other_expenses: list[PublicOtherExpenseResponse] = Field(
        default_factory=list,
        description='Прочие траты',
    )
    repairs: list[PublicRepairResponse] = Field(
        default_factory=list,
        description='Ремонты и обслуживание',
    )
    fuel_records: list[PublicFuelRecordResponse] = Field(
        default_factory=list,
        description='Заправки',
    )
    register_url: str = Field(
        ...,
        description='Ссылка на регистрацию',
    )
