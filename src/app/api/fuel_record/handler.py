import logging

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.api.fuel_record.schema import (
    FuelRecordCreateRequest,
    FuelRecordResponse,
    FuelRecordUpdateRequest,
)
from app.common.middleware import (
    verify_fuel_record_access,
    verify_fuel_record_view_access,
    verify_vehicle_access,
    verify_vehicle_view_access,
)
from app.db.database import get_db
from app.services.dto import FuelRecordDTO, VehicleDTO
from app.services.fuel_record_service import FuelRecordService

logger = logging.getLogger(__name__)


class FuelRecordHandler:
    """Хэндлер для операций с заправками."""

    @staticmethod
    def _to_response(record: FuelRecordDTO) -> FuelRecordResponse:
        """Преобразовать DTO в Response."""
        return FuelRecordResponse(
            id=record.id,  # type: ignore[arg-type]
            vehicle_id=record.vehicle_id,
            fuel_date=record.fuel_date,
            km_at_fuel=record.km_at_fuel,
            liters=record.liters,
            total_cost=record.total_cost,
            consumption_l_per_100km=record.consumption_l_per_100km,
        )

    async def create_fuel_record(
        self,
        request: FuelRecordCreateRequest,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> FuelRecordResponse:
        """Создать запись о заправке."""
        fuel_service = FuelRecordService(db)

        try:
            record = fuel_service.create(vehicle.id, request, vehicle)  # type: ignore[arg-type]
            return self._to_response(record)
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
            logger.exception('Failed to create fuel record')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось создать заправку',
            )

    async def get_vehicle_fuel_records(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> list[FuelRecordResponse]:
        """Получить все заправки автомобиля."""
        fuel_service = FuelRecordService(db)

        try:
            records = fuel_service.get_by_vehicle(vehicle.id)  # type: ignore[arg-type]
            return [self._to_response(record) for record in records]
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to get vehicle fuel records')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось получить заправки',
            )

    async def get_fuel_record(
        self,
        record: FuelRecordDTO = Depends(verify_fuel_record_view_access),
    ) -> FuelRecordResponse:
        """Получить заправку по ID."""
        return self._to_response(record)

    async def update_fuel_record(
        self,
        request: FuelRecordUpdateRequest,
        db: Session = Depends(get_db),
        record: FuelRecordDTO = Depends(verify_fuel_record_access),
    ) -> FuelRecordResponse:
        """Частично обновить запись о заправке."""
        fuel_service = FuelRecordService(db)

        try:
            update_data = request.model_dump(exclude_none=True)
            updated = fuel_service.update(record.id, **update_data)  # type: ignore[arg-type]
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Заправка не найдена',
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
            logger.exception('Failed to update fuel record')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить заправку',
            )

    async def delete_fuel_record(
        self,
        db: Session = Depends(get_db),
        record: FuelRecordDTO = Depends(verify_fuel_record_access),
    ) -> dict[str, str]:
        """Удалить запись о заправке."""
        fuel_service = FuelRecordService(db)

        try:
            fuel_service.delete(record.id)  # type: ignore[arg-type]
            return {'status': 'ok', 'message': f'Заправка {record.id} удалена'}
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception('Failed to delete fuel record')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось удалить заправку',
            )


fuel_record_handler = FuelRecordHandler()
