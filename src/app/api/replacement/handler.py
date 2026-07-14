from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.replacement.schema import (
    ReplacementResponse,
    UpdateReplacementRequest,
    ReplacementsBulkRequest,
)
from app.db.database import get_db
from app.db.models import UserDB
from app.auth.jwt import get_current_user
from app.services.dto import ReplacementDTO, VehicleDTO
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.common.enums import StatusEnum
from app.common.utils.calculator import StatusCalculator
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
                status=StatusEnum.REPLACED.value,
                status_message="📌 Заменено (предыдущая запись)",
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
            status=status_data["status"],
            status_message=status_data["status_message"]
        )

    def _check_vehicle_access(
        self,
        vehicle_id: int,
        current_user: UserDB,
        vehicle_service: VehicleService,
    ) -> None:
        """Проверить, что автомобиль принадлежит пользователю."""
        vehicle = vehicle_service.get_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Vehicle not found',
            )
        if vehicle.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

    async def create_replacements(
        self,
        vehicle_id: int,
        request: ReplacementsBulkRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> List[ReplacementResponse]:
        """Создать несколько замен сразу (например, при ТО)."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            self._check_vehicle_access(vehicle_id, current_user, vehicle_service)

            results = []
            for replacement_request in request.replacements:
                replacement_dto = replacement_service.create(vehicle_id, replacement_request)
                vehicle = vehicle_service.get_active_by_id(vehicle_id)
                results.append(self._to_response(replacement_dto, vehicle))

            check_vehicle_notifications(db, vehicle_id)
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
        vehicle_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> List[ReplacementResponse]:
        """Получить все замены для автомобиля с расчётом статусов."""
        vehicle_service = VehicleService(db)
        replacement_service = ReplacementService(db)

        try:
            self._check_vehicle_access(vehicle_id, current_user, vehicle_service)

            vehicle = vehicle_service.get_active_by_id(vehicle_id)
            replacements_dto = replacement_service.get_by_vehicle(vehicle_id)

            latest_per_type: dict[str, int] = {}
            for r in replacements_dto:
                prev = latest_per_type.get(r.component_type.value)
                if prev is None or r.km_at_replacement > prev:
                    latest_per_type[r.component_type.value] = r.km_at_replacement

            result = []
            for r in replacements_dto:
                is_latest = latest_per_type.get(r.component_type.value) == r.km_at_replacement
                result.append(self._to_response(r, vehicle, is_latest))
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
        replacement_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> ReplacementResponse:
        """Получить конкретную замену по ID."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            replacement_dto = replacement_service.get_by_id(replacement_id)
            if not replacement_dto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Replacement not found',
                )

            self._check_vehicle_access(replacement_dto.vehicle_id, current_user, vehicle_service)

            vehicle = vehicle_service.get_active_by_id(replacement_dto.vehicle_id)
            return self._to_response(replacement_dto, vehicle)
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to get replacement: {err}',
            )

    async def update_replacement(
        self,
        replacement_id: int,
        request: UpdateReplacementRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> ReplacementResponse:
        """Обновить запись о замене."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            replacement_dto = replacement_service.get_by_id(replacement_id)
            if not replacement_dto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Replacement not found',
                )

            self._check_vehicle_access(replacement_dto.vehicle_id, current_user, vehicle_service)

            update_data = request.model_dump(exclude_none=True)
            replacement_dto = replacement_service.update(replacement_id, **update_data)

            vehicle = vehicle_service.get_active_by_id(replacement_dto.vehicle_id)

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
        replacement_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> dict[str, str]:
        """Удалить запись о замене."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            replacement_dto = replacement_service.get_by_id(replacement_id)
            if not replacement_dto:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Replacement not found',
                )

            self._check_vehicle_access(replacement_dto.vehicle_id, current_user, vehicle_service)

            replacement_service.delete(replacement_id)

            return {'status': 'ok', 'message': f'Replacement {replacement_id} has been deleted'}
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to delete replacement: {err}',
            )


replacement_handler = ReplacementHandler()
