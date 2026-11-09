import logging
from typing import List

from fastapi import HTTPException, status, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.api.replacement.mapper import build_replacement_response
from app.api.replacement.schema import (
    ReplacementResponse,
    UpdateReplacementRequest,
    ReplacementsBulkRequest,
)
from app.db.database import get_db
from app.services.dto import ReplacementDTO, VehicleDTO
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.common.middleware import (
    verify_vehicle_access,
    verify_vehicle_view_access,
    verify_replacement_access,
    verify_replacement_view_access,
)
from app.services.notification_service import check_vehicle_notifications_background

logger = logging.getLogger(__name__)


class ReplacementHandler:
    """Хэндлер для операций с заменами."""

    def _to_response(
        self,
        replacement_dto: ReplacementDTO,
        vehicle: VehicleDTO,
        is_latest: bool = True,
        km_traveled: int | None = None,
    ) -> ReplacementResponse:
        """Преобразовать DTO в Response с расчётом статуса."""
        return build_replacement_response(
            replacement_dto,
            vehicle,
            is_latest=is_latest,
            km_traveled=km_traveled,
        )

    async def create_replacements(
        self,
        request: ReplacementsBulkRequest,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
        background_tasks: BackgroundTasks = BackgroundTasks(),
    ) -> List[ReplacementResponse]:
        """Создать несколько замен сразу (например, при ТО)."""
        replacement_service = ReplacementService(db)

        try:
            created = []
            for replacement_request in request.replacements:
                created.append(replacement_service.create(
                    vehicle.id,
                    replacement_request,
                    vehicle,
                    commit=False,
                ))

            db.commit()
            km_traveled = replacement_service.get_tire_km_traveled(vehicle.id, vehicle.current_km)
            results = [
                build_replacement_response(
                    replacement_dto,
                    vehicle,
                    km_traveled=km_traveled.get(replacement_dto.id or 0),
                )
                for replacement_dto in created
            ]

            background_tasks.add_task(
                check_vehicle_notifications_background,
                vehicle.id,
            )
            return results
        except ValueError as err:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception('Failed to create replacements')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось создать замены',
            )

    async def get_vehicle_replacements(
        self,
        limit: int | None = Query(None, ge=1, le=1000),
        offset: int | None = Query(None, ge=0),
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> List[ReplacementResponse]:
        """Получить все замены для автомобиля с расчётом статусов."""
        replacement_service = ReplacementService(db)

        try:
            latest_ids = replacement_service.get_latest_replacement_ids(vehicle.id)
            replacements_dto = replacement_service.get_by_vehicle(
                vehicle.id,
                limit=limit,
                offset=offset,
            )
            km_traveled = replacement_service.get_tire_km_traveled(vehicle.id, vehicle.current_km)

            return [
                build_replacement_response(
                    replacement,
                    vehicle,
                    is_latest=replacement.id in latest_ids,
                    km_traveled=km_traveled.get(replacement.id or 0),
                )
                for replacement in replacements_dto
            ]
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to get vehicle replacements')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось получить замены',
            )

    async def get_replacement(
        self,
        db: Session = Depends(get_db),
        replacement: ReplacementDTO = Depends(verify_replacement_view_access),
    ) -> ReplacementResponse:
        """Получить конкретную замену по ID."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            vehicle = vehicle_service.get_by_id(replacement.vehicle_id)
            km_traveled = replacement_service.get_tire_km_traveled(vehicle.id, vehicle.current_km)
            return build_replacement_response(
                replacement,
                vehicle,
                km_traveled=km_traveled.get(replacement.id or 0),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to get replacement')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось получить замену',
            )

    async def update_replacement(
        self,
        request: UpdateReplacementRequest,
        db: Session = Depends(get_db),
        replacement: ReplacementDTO = Depends(verify_replacement_access),
        background_tasks: BackgroundTasks = BackgroundTasks(),
    ) -> ReplacementResponse:
        """Обновить запись о замене."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            vehicle = vehicle_service.get_by_id(replacement.vehicle_id)

            replacement_dto = replacement_service.update(replacement.id, request)
            vehicle = vehicle_service.get_by_id(replacement_dto.vehicle_id)
            km_traveled = replacement_service.get_tire_km_traveled(vehicle.id, vehicle.current_km)

            background_tasks.add_task(
                check_vehicle_notifications_background,
                replacement_dto.vehicle_id,
            )

            return build_replacement_response(
                replacement_dto,
                vehicle,
                km_traveled=km_traveled.get(replacement_dto.id or 0),
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to update replacement')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить замену',
            )

    async def delete_replacement(
        self,
        db: Session = Depends(get_db),
        replacement: ReplacementDTO = Depends(verify_replacement_access),
    ) -> dict[str, str]:
        """Удалить запись о замене."""
        replacement_service = ReplacementService(db)

        try:
            replacement_service.delete(replacement.id)

            return {'status': 'ok', 'message': f'Замена {replacement.id} удалена'}
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to delete replacement')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось удалить замену',
            )


replacement_handler = ReplacementHandler()
