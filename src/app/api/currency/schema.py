from datetime import datetime

from pydantic import BaseModel, Field

from app.common.enums import Currency


class ConversionPreviewResponse(BaseModel):
    """Предпросмотр смены валюты."""

    from_currency: Currency
    to_currency: Currency
    rate: float | None = Field(None, description='Сколько целевой валюты за 1 единицу текущей')
    to_rub_rate: float | None = Field(None, description='Рублей за 1 единицу целевой валюты')
    records_count: int = Field(0, description='Сколько денежных записей будет пересчитано')
    vehicles_count: int = Field(0, description='Сколько автомобилей затронуто')
    source: str = Field(..., description='Источник курса')
    fetched_at: datetime | None = Field(None, description='Время получения курса')
    stale: bool = Field(False, description='Использован устаревший или резервный курс')
