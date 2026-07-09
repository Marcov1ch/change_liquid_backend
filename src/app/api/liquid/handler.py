from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.liquid.schema import (
    LiquidReplacementResponse,
    UpdateLiquidReplacementRequest,
    ReplacementsRequest,
)
from app.db.database import get_db
from app.db.models import UserDB
from app.auth.jwt import get_current_user
from app.common.enums import StatusEnum
from app.common.liquid_config import LIQUIDS_CONFIG
from app.services.dto import ReplacementDTO, VehicleDTO
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.common.utils.calculator import LiquidCalculator


class ReplacementHandler:
    """Хэндлер для операций с заменами жидкостей."""
    def _to_response(
        self,
        replacement_dto: ReplacementDTO,
        current_km: int,
        vehicle: VehicleDTO,
        is_latest: bool = True,
    ) -> LiquidReplacementResponse:
        """Преобразовать DTO в Response с расчётом статуса."""
        config = next((c for c in LIQUIDS_CONFIG if c.type == replacement_dto.liquid_type), None)
        interval = getattr(vehicle, config.interval_field) if config else replacement_dto.interval_km

        if not is_latest:
            return LiquidReplacementResponse(
                id=replacement_dto.id,
                vehicle_id=replacement_dto.vehicle_id,
                liquid_type=replacement_dto.liquid_type,
                liquid_name=replacement_dto.liquid_name,
                liquid_price=replacement_dto.liquid_price,
                work_price=replacement_dto.work_price,
                replacement_date=replacement_dto.replacement_date,
                km_at_replacement=replacement_dto.km_at_replacement,
                interval_km=replacement_dto.interval_km,
                next_replacement_km=replacement_dto.km_at_replacement + interval,
                km_remaining=0,
                status=StatusEnum.REPLACED.value,
                status_message="📌 Заменено (предыдущая запись)"
            )

        status_data = LiquidCalculator.calculate_status(
            km_at_replacement=replacement_dto.km_at_replacement,
            interval_km=interval,
            current_km=current_km
        )

        return LiquidReplacementResponse(
            id=replacement_dto.id,
            vehicle_id=replacement_dto.vehicle_id,
            liquid_type=replacement_dto.liquid_type,
            liquid_name=replacement_dto.liquid_name,
            liquid_price=replacement_dto.liquid_price,
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
        request: ReplacementsRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> List[LiquidReplacementResponse]:
        """Создать несколько замен сразу (например, при ТО)."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            self._check_vehicle_access(vehicle_id, current_user, vehicle_service)

            results = []
            for replacement_request in request.replacements:
                replacement_dto = replacement_service.create(vehicle_id, replacement_request)
                vehicle = vehicle_service.get_active_by_id(vehicle_id)
                results.append(self._to_response(replacement_dto, vehicle.current_km, vehicle))
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
    ) -> List[LiquidReplacementResponse]:
        """Получить все замены для автомобиля с расчётом статусов."""
        vehicle_service = VehicleService(db)
        replacement_service = ReplacementService(db)

        try:
            self._check_vehicle_access(vehicle_id, current_user, vehicle_service)

            vehicle = vehicle_service.get_active_by_id(vehicle_id)
            replacements_dto = replacement_service.get_by_vehicle(vehicle_id)

            latest_per_type: dict[str, int] = {}
            for r in replacements_dto:
                if r.liquid_type.value not in latest_per_type or r.km_at_replacement > latest_per_type[r.liquid_type.value]:
                    latest_per_type[r.liquid_type.value] = r.km_at_replacement

            return [
                self._to_response(r, vehicle.current_km, vehicle, is_latest=(r.km_at_replacement == latest_per_type.get(r.liquid_type.value)))
                for r in replacements_dto
            ]
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
    ) -> LiquidReplacementResponse:
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
            return self._to_response(replacement_dto, vehicle.current_km, vehicle)
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
        request: UpdateLiquidReplacementRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> LiquidReplacementResponse:
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
            return self._to_response(replacement_dto, vehicle.current_km, vehicle)
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
