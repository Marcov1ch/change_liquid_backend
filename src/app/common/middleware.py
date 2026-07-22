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


def verify_vehicle_access(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> VehicleDTO:
    vehicle_service = VehicleService(db)
    vehicle = vehicle_service.get_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )
    if vehicle.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return vehicle


def verify_replacement_access(
    replacement_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> ReplacementDTO:
    replacement_service = ReplacementService(db)
    vehicle_service = VehicleService(db)

    replacement = replacement_service.get_by_id(replacement_id)
    if not replacement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Replacement not found",
        )

    vehicle = vehicle_service.get_by_id(replacement.vehicle_id)
    if not vehicle or vehicle.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return replacement
