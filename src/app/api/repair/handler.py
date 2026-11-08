import logging

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.api.repair.schema import (
    RepairCreateRequest,
    RepairResponse,
    RepairUpdateRequest,
)
from app.common.middleware import (
    verify_repair_access,
    verify_repair_view_access,
    verify_vehicle_access,
    verify_vehicle_view_access,
)
from app.db.database import get_db
from app.services.dto import RepairDTO, VehicleDTO
from app.services.repair_service import RepairService

logger = logging.getLogger(__name__)


class RepairHandler:
    """Хэндлер для операций с ремонтами."""

    @staticmethod
    def _to_response(repair: RepairDTO) -> RepairResponse:
        """Преобразовать DTO в Response."""
        return RepairResponse(
            id=repair.id,  # type: ignore[arg-type]
            vehicle_id=repair.vehicle_id,
            repair_date=repair.repair_date,
            km_at_repair=repair.km_at_repair,
            description=repair.description,
            work_cost=repair.work_cost,
            parts_cost=repair.parts_cost,
            component_types=repair.component_types,
        )

    async def create_repair(
        self,
        request: RepairCreateRequest,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> RepairResponse:
        """Создать ремонт."""
        repair_service = RepairService(db)

        try:
            repair = repair_service.create(vehicle.id, request, vehicle)  # type: ignore[arg-type]
            return self._to_response(repair)
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
            logger.exception('Failed to create repair')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось создать ремонт',
            )

    async def get_vehicle_repairs(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> list[RepairResponse]:
        """Получить все ремонты автомобиля."""
        repair_service = RepairService(db)

        try:
            repairs = repair_service.get_by_vehicle(vehicle.id)  # type: ignore[arg-type]
            return [self._to_response(repair) for repair in repairs]
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to get vehicle repairs')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось получить ремонты',
            )

    async def get_repair(
        self,
        repair: RepairDTO = Depends(verify_repair_view_access),
    ) -> RepairResponse:
        """Получить ремонт по ID."""
        return self._to_response(repair)

    async def update_repair(
        self,
        request: RepairUpdateRequest,
        db: Session = Depends(get_db),
        repair: RepairDTO = Depends(verify_repair_access),
    ) -> RepairResponse:
        """Полностью обновить ремонт."""
        repair_service = RepairService(db)

        try:
            updated = repair_service.update(repair.id, request)  # type: ignore[arg-type]
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Ремонт не найден',
                )
            return self._to_response(updated)
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
            logger.exception('Failed to update repair')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить ремонт',
            )

    async def delete_repair(
        self,
        db: Session = Depends(get_db),
        repair: RepairDTO = Depends(verify_repair_access),
    ) -> dict[str, str]:
        """Удалить ремонт."""
        repair_service = RepairService(db)

        try:
            repair_service.delete(repair.id)  # type: ignore[arg-type]
            return {'status': 'ok', 'message': f'Ремонт {repair.id} удалён'}
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception('Failed to delete repair')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось удалить ремонт',
            )


repair_handler = RepairHandler()
