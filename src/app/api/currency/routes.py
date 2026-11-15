from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.currency.schema import ConversionPreviewResponse
from app.auth.jwt import get_current_user
from app.common.enums import Currency
from app.db.database import get_db
from app.db.models import UserDB
from app.services.currency_conversion_service import CurrencyConversionService

router = APIRouter()


@router.get(
    '/currency/conversion-preview',
    response_model=ConversionPreviewResponse,
    tags=['currency'],
)
def get_conversion_preview(
    target: Currency = Query(..., description='Целевая валюта'),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> ConversionPreviewResponse:
    """Вернуть курс и объём данных для смены валюты."""
    try:
        preview = CurrencyConversionService(db).preview(current_user, target.value)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(err),
        )
    return ConversionPreviewResponse(
        from_currency=preview.from_currency,
        to_currency=preview.to_currency,
        rate=preview.rate,
        to_rub_rate=preview.to_rub_rate,
        records_count=preview.records_count,
        vehicles_count=preview.vehicles_count,
        source=preview.source,
        fetched_at=preview.fetched_at,
        stale=preview.stale,
    )
