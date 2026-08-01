import logging
import time

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.database import get_db
from app.auth.jwt import get_current_user
from app.db.models import UserDB
from app.services.vehicle_service import VehicleService
from app.services.replacement_service import ReplacementService
from app.services.dto import VehicleDTO, ReplacementDTO

logger = logging.getLogger(__name__)

_MSG_VEHICLE_NOT_FOUND = 'Автомобиль не найден'
_MSG_VEHICLE_ARCHIVED = 'Автомобиль находится в архиве'
_MSG_REPLACEMENT_NOT_FOUND = 'Замена не найдена'
_MSG_ACCESS_DENIED = 'Доступ запрещён'


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration * 1000,
        )
        return response


def _verify_vehicle_access(
    db: Session,
    current_user: UserDB,
    vehicle_id: int,
    require_active: bool,
) -> VehicleDTO:
    vehicle_service = VehicleService(db)
    vehicle = vehicle_service.get_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_MSG_VEHICLE_NOT_FOUND,
        )
    if vehicle.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_MSG_ACCESS_DENIED,
        )
    if require_active and not vehicle.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_MSG_VEHICLE_ARCHIVED,
        )
    return vehicle


def verify_vehicle_access(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> VehicleDTO:
    """Проверка доступа к авто; операции с архивным авто запрещены."""
    return _verify_vehicle_access(db, current_user, vehicle_id, require_active=True)


def verify_vehicle_view_access(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> VehicleDTO:
    """Проверка доступа к авто; просмотр архивного авто разрешён."""
    return _verify_vehicle_access(db, current_user, vehicle_id, require_active=False)


def _verify_replacement_access(
    db: Session,
    current_user: UserDB,
    replacement_id: int,
    require_active: bool,
) -> ReplacementDTO:
    replacement_service = ReplacementService(db)
    vehicle_service = VehicleService(db)

    replacement = replacement_service.get_by_id(replacement_id)
    if not replacement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_MSG_REPLACEMENT_NOT_FOUND,
        )

    vehicle = vehicle_service.get_by_id(replacement.vehicle_id)
    if not vehicle or vehicle.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_MSG_ACCESS_DENIED,
        )
    if require_active and not vehicle.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_MSG_VEHICLE_ARCHIVED,
        )

    return replacement


def verify_replacement_access(
    replacement_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> ReplacementDTO:
    """Проверка доступа к замене; операции с архивным авто запрещены."""
    return _verify_replacement_access(db, current_user, replacement_id, require_active=True)


def verify_replacement_view_access(
    replacement_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> ReplacementDTO:
    """Проверка доступа к замене; просмотр замен архивного авто разрешён."""
    return _verify_replacement_access(db, current_user, replacement_id, require_active=False)
