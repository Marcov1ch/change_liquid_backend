from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.replacement.schema import (
    ReplacementResponse,
    UpdateReplacementRequest,
    ReplacementsBulkRequest,
)
from app.db.database import get_db
from app.services.dto import ReplacementDTO, VehicleDTO
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.common.middleware import verify_vehicle_access, verify_replacement_access
from app.common.enums import StatusEnum, ComponentType
from app.common.utils.calculator import StatusCalculator
from app.common.utils.interval_utils import get_last_per_type
from app.services.notification_service import check_vehicle_notifications


class ReplacementHandler:
    """Хэндлер для операций с заменами."""

    def _to_response(
        self,
        replacement_dto: ReplacementDTO,
        vehicle: VehicleDTO,
        is_latest: bool = True,
    ) -> ReplacementResponse:
        """Преобразовать DTO в Response с расчётом статуса."""
        is_tire = replacement_dto.component_type == ComponentType.TIRE_CHANGE

        if not is_latest:
            return ReplacementResponse(
                id=replacement_dto.id,
                vehicle_id=replacement_dto.vehicle_id,
                component_type=replacement_dto.component_type,
                component_name=replacement_dto.component_name,
                component_price=replacement_dto.component_price,
                work_price=replacement_dto.work_price,
                replacement_date=replacement_dto.replacement_date,
                km_at_replacement=replacement_dto.km_at_replacement,
                interval_km=replacement_dto.interval_km,
                next_replacement_km=0,
                km_remaining=0,
                next_change_date=replacement_dto.next_change_date,
                days_remaining=None,
                status=StatusEnum.REPLACED.value,
                status_message="📌 Заменено",
            )

        if is_tire:
            status_data = StatusCalculator.calculate_date_status(
                replacement_dto.next_change_date,
            )
            return ReplacementResponse(
                id=replacement_dto.id,
                vehicle_id=replacement_dto.vehicle_id,
                component_type=replacement_dto.component_type,
                component_name=replacement_dto.component_name,
                component_price=replacement_dto.component_price,
                work_price=replacement_dto.work_price,
                replacement_date=replacement_dto.replacement_date,
                km_at_replacement=replacement_dto.km_at_replacement,
                interval_km=replacement_dto.interval_km,
                next_replacement_km=0,
                km_remaining=0,
                next_change_date=status_data["next_change_date"],
                days_remaining=status_data["days_remaining"],
                status=status_data["status"],
                status_message=status_data["status_message"],
            )

        interval = vehicle.intervals.get(replacement_dto.component_type.value, 0)
        status_data = StatusCalculator.calculate_status(
            km_at_replacement=replacement_dto.km_at_replacement,
            interval_km=interval,
            current_km=vehicle.current_km,
        )

        return ReplacementResponse(
            id=replacement_dto.id,
            vehicle_id=replacement_dto.vehicle_id,
            component_type=replacement_dto.component_type,
            component_name=replacement_dto.component_name,
            component_price=replacement_dto.component_price,
            work_price=replacement_dto.work_price,
            replacement_date=replacement_dto.replacement_date,
            km_at_replacement=replacement_dto.km_at_replacement,
            interval_km=replacement_dto.interval_km,
            next_replacement_km=status_data["next_replacement_km"],
            km_remaining=status_data["km_remaining"],
            next_change_date=None,
            days_remaining=None,
            status=status_data["status"],
            status_message=status_data["status_message"]
        )

    async def create_replacements(
        self,
        request: ReplacementsBulkRequest,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> List[ReplacementResponse]:
        """Создать несколько замен сразу (например, при ТО)."""
        replacement_service = ReplacementService(db)

        try:
            results = []
            for replacement_request in request.replacements:
                replacement_dto = replacement_service.create(vehicle.id, replacement_request, vehicle)
                results.append(self._to_response(replacement_dto, vehicle))

            check_vehicle_notifications(db, vehicle.id)
            return results
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to create replacements: {err}',
            )

    async def get_vehicle_replacements(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> List[ReplacementResponse]:
        """Получить все замены для автомобиля с расчётом статусов."""
        replacement_service = ReplacementService(db)

        try:
            replacements_dto = replacement_service.get_by_vehicle(vehicle.id)

            last_by_type = get_last_per_type(replacements_dto)

            result = []
            for replacement in replacements_dto:
                last = last_by_type.get(replacement.component_type)
                is_latest = last is not None and (replacement.km_at_replacement, replacement.id or 0) == (last.km_at_replacement, last.id or 0)
                result.append(self._to_response(replacement, vehicle, is_latest))
            return result
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to get replacements: {err}',
            )

    async def get_replacement(
        self,
        db: Session = Depends(get_db),
        replacement: ReplacementDTO = Depends(verify_replacement_access),
    ) -> ReplacementResponse:
        """Получить конкретную замену по ID."""
        vehicle_service = VehicleService(db)

        try:
            vehicle = vehicle_service.get_by_id(replacement.vehicle_id)
            return self._to_response(replacement, vehicle)
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to get replacement: {err}',
            )

    async def update_replacement(
        self,
        request: UpdateReplacementRequest,
        db: Session = Depends(get_db),
        replacement: ReplacementDTO = Depends(verify_replacement_access),
    ) -> ReplacementResponse:
        """Обновить запись о замене."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            vehicle = vehicle_service.get_by_id(replacement.vehicle_id)

            update_data = request.model_dump(exclude_none=True)
            replacement_dto = replacement_service.update(replacement.id, **update_data)

            check_vehicle_notifications(db, replacement_dto.vehicle_id)

            return self._to_response(replacement_dto, vehicle)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to update replacement: {err}',
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

            return {'status': 'ok', 'message': f'Replacement {replacement.id} has been deleted'}
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to delete replacement: {err}',
            )


replacement_handler = ReplacementHandler()
