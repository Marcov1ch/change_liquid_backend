import logging
import time
from typing import Protocol, TypeVar

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.database import get_db
from app.auth.jwt import get_current_user
from app.db.models import UserDB
from app.services.vehicle_service import VehicleService
from app.services.replacement_service import ReplacementService
from app.services.other_expense_service import OtherExpenseService
from app.services.repair_service import RepairService
from app.services.fuel_record_service import FuelRecordService
from app.services.tire_set_service import TireSetService
from app.services.dto import (
    VehicleDTO,
    ReplacementDTO,
    OtherExpenseDTO,
    RepairDTO,
    FuelRecordDTO,
    TireSetDTO,
)

logger = logging.getLogger(__name__)

_MSG_VEHICLE_NOT_FOUND = 'Автомобиль не найден'
_MSG_VEHICLE_ARCHIVED = 'Автомобиль находится в архиве'
_MSG_REPLACEMENT_NOT_FOUND = 'Замена не найдена'
_MSG_OTHER_EXPENSE_NOT_FOUND = 'Трата не найдена'
_MSG_REPAIR_NOT_FOUND = 'Ремонт не найден'
_MSG_FUEL_RECORD_NOT_FOUND = 'Заправка не найдена'
_MSG_TIRE_SET_NOT_FOUND = 'Комплект шин не найден'
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


def _require_vehicle_access(
    vehicle: VehicleDTO | None,
    current_user: UserDB,
    require_active: bool,
    missing_status: int = status.HTTP_404_NOT_FOUND,
    missing_detail: str = _MSG_VEHICLE_NOT_FOUND,
) -> VehicleDTO:
    """Проверить существование авто, владельца и активность."""
    if not vehicle:
        raise HTTPException(status_code=missing_status, detail=missing_detail)
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


class _HasVehicleId(Protocol):
    vehicle_id: int


_RelatedEntity = TypeVar('_RelatedEntity', bound=_HasVehicleId)


def _require_related_entity_access(
    entity: _RelatedEntity | None,
    current_user: UserDB,
    require_active: bool,
    not_found_detail: str,
    vehicle_service: VehicleService,
) -> _RelatedEntity:
    """Проверить наличие связанной сущности и доступ к её автомобилю."""
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )
    _require_vehicle_access(
        vehicle_service.get_by_id(entity.vehicle_id),
        current_user,
        require_active,
        missing_status=status.HTTP_403_FORBIDDEN,
        missing_detail=_MSG_ACCESS_DENIED,
    )
    return entity


def _verify_vehicle_access(
    db: Session,
    current_user: UserDB,
    vehicle_id: int,
    require_active: bool,
) -> VehicleDTO:
    vehicle_service = VehicleService(db)
    return _require_vehicle_access(
        vehicle_service.get_by_id(vehicle_id),
        current_user,
        require_active,
    )


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
    return _require_related_entity_access(
        ReplacementService(db).get_by_id(replacement_id),
        current_user,
        require_active,
        _MSG_REPLACEMENT_NOT_FOUND,
        VehicleService(db),
    )


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


def _verify_other_expense_access(
    db: Session,
    current_user: UserDB,
    expense_id: int,
    require_active: bool,
) -> OtherExpenseDTO:
    return _require_related_entity_access(
        OtherExpenseService(db).get_by_id(expense_id),
        current_user,
        require_active,
        _MSG_OTHER_EXPENSE_NOT_FOUND,
        VehicleService(db),
    )


def verify_other_expense_access(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> OtherExpenseDTO:
    """Проверка доступа к прочей трате; операции с архивным авто запрещены."""
    return _verify_other_expense_access(db, current_user, expense_id, require_active=True)


def verify_other_expense_view_access(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> OtherExpenseDTO:
    """Проверка доступа к прочей трате; просмотр трат архивного авто разрешён."""
    return _verify_other_expense_access(db, current_user, expense_id, require_active=False)


def _verify_repair_access(
    db: Session,
    current_user: UserDB,
    repair_id: int,
    require_active: bool,
) -> RepairDTO:
    return _require_related_entity_access(
        RepairService(db).get_by_id(repair_id),
        current_user,
        require_active,
        _MSG_REPAIR_NOT_FOUND,
        VehicleService(db),
    )


def verify_repair_access(
    repair_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> RepairDTO:
    """Проверка доступа к ремонту; операции с архивным авто запрещены."""
    return _verify_repair_access(db, current_user, repair_id, require_active=True)


def verify_repair_view_access(
    repair_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> RepairDTO:
    """Проверка доступа к ремонту; просмотр ремонтов архивного авто разрешён."""
    return _verify_repair_access(db, current_user, repair_id, require_active=False)


def _verify_fuel_record_access(
    db: Session,
    current_user: UserDB,
    record_id: int,
    require_active: bool,
) -> FuelRecordDTO:
    return _require_related_entity_access(
        FuelRecordService(db).get_by_id(record_id),
        current_user,
        require_active,
        _MSG_FUEL_RECORD_NOT_FOUND,
        VehicleService(db),
    )


def verify_fuel_record_access(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> FuelRecordDTO:
    """Проверка доступа к заправке; операции с архивным авто запрещены."""
    return _verify_fuel_record_access(db, current_user, record_id, require_active=True)


def verify_fuel_record_view_access(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> FuelRecordDTO:
    """Проверка доступа к заправке; просмотр заправок архивного авто разрешён."""
    return _verify_fuel_record_access(db, current_user, record_id, require_active=False)


def _verify_tire_set_access(
    db: Session,
    current_user: UserDB,
    tire_set_id: int,
    require_active: bool,
) -> TireSetDTO:
    return _require_related_entity_access(
        TireSetService(db).get_by_id(tire_set_id),
        current_user,
        require_active,
        _MSG_TIRE_SET_NOT_FOUND,
        VehicleService(db),
    )


def verify_tire_set_access(
    tire_set_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> TireSetDTO:
    """Проверка доступа к комплекту шин; операции с архивным авто запрещены."""
    return _verify_tire_set_access(db, current_user, tire_set_id, require_active=True)


def verify_tire_set_view_access(
    tire_set_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> TireSetDTO:
    """Проверка доступа к комплекту шин; просмотр архивного авто разрешён."""
    return _verify_tire_set_access(db, current_user, tire_set_id, require_active=False)
