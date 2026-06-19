from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.api.liquid.schema import (
    LiquidReplacementResponse,
    UpdateLiquidReplacementRequest,
    ReplacementsRequest,
)
from app.db.database import get_db
from app.services.dto import ReplacementDTO
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.common.utils.calculator import LiquidCalculator


class ReplacementHandler:
    """Хэндлер для операций с заменами жидкостей."""
    async def create_replacements(
        self,
        vehicle_id: int,
        request: ReplacementsRequest,
        db: Session = Depends(get_db)
    ) -> List[LiquidReplacementResponse]:
        """Создать несколько замен сразу (например, при ТО)."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            results = []
            for replacement_request in request.replacements:
                replacement_dto = replacement_service.create(vehicle_id, replacement_request)
                vehicle = vehicle_service.get_active_by_id(vehicle_id)

                if not vehicle:
                    raise HTTPException(status_code=404, detail='Vehicle not found')

                results.append(self._to_response(replacement_dto, vehicle.current_km))
            return results
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f'Failed to create replacements: {err}')

    async def get_vehicle_replacements(
        self,
        vehicle_id: int,
        db: Session = Depends(get_db)
    ) -> List[LiquidReplacementResponse]:
        """Получить все замены для автомобиля с расчётом статусов."""
        vehicle_service = VehicleService(db)
        replacement_service = ReplacementService(db)

        try:
            vehicle = vehicle_service.get_active_by_id(vehicle_id)
            if not vehicle:
                raise HTTPException(status_code=404, detail='Vehicle not found')

            replacements_dto = replacement_service.get_by_vehicle(vehicle_id)

            return [self._to_response(r, vehicle.current_km) for r in replacements_dto]
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f'Failed to get replacements: {err}')

    async def get_replacement(
        self,
        replacement_id: int,
        db: Session = Depends(get_db)
    ) -> LiquidReplacementResponse:
        """Получить конкретную замену по ID."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            replacement_dto = replacement_service.get_by_id(replacement_id)
            if not replacement_dto:
                raise HTTPException(status_code=404, detail='Replacement not found')

            vehicle = vehicle_service.get_active_by_id(replacement_dto.vehicle_id)
            if not vehicle:
                raise HTTPException(status_code=404, detail='Vehicle not found')

            return self._to_response(replacement_dto, vehicle.current_km)
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f'Failed to get replacement: {err}')

    async def update_replacement(
        self,
        replacement_id: int,
        request: UpdateLiquidReplacementRequest,
        db: Session = Depends(get_db)
    ) -> LiquidReplacementResponse:
        """Обновить запись о замене."""
        replacement_service = ReplacementService(db)
        vehicle_service = VehicleService(db)

        try:
            update_data = request.model_dump(exclude_none=True)
            replacement_dto = replacement_service.update(replacement_id, **update_data)

            if not replacement_dto:
                raise HTTPException(status_code=404, detail='Replacement not found')

            vehicle = vehicle_service.get_active_by_id(replacement_dto.vehicle_id)
            if not vehicle:
                raise HTTPException(status_code=404, detail='Vehicle not found')

            return self._to_response(replacement_dto, vehicle.current_km)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f'Failed to update replacement: {err}')

    async def delete_replacement(
        self,
        replacement_id: int,
        db: Session = Depends(get_db)
    ) -> dict[str, str]:
        """Удалить запись о замене."""
        replacement_service = ReplacementService(db)

        try:
            replacement_dto = replacement_service.get_by_id(replacement_id)
            if not replacement_dto:
                raise HTTPException(status_code=404, detail='Replacement not found')

            replacement_service.delete(replacement_id)

            return {'status': 'ok', 'message': f'Replacement {replacement_id} has been deleted'}
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(status_code=500, detail=f'Failed to delete replacement: {err}')

    def _to_response(
        self,
        replacement_dto: ReplacementDTO,
        current_km: int,
    ) -> LiquidReplacementResponse:
        """Преобразовать DTO в Response с расчётом статуса."""
        status_data = LiquidCalculator.calculate_status(
            km_at_replacement=replacement_dto.km_at_replacement,
            interval_km=replacement_dto.interval_km,
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


replacement_handler = ReplacementHandler()
