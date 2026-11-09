import logging

from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.api.replacement.mapper import build_replacement_response
from app.api.tire_set.schema import (
    TireInstallRequest,
    TireInstallResponse,
    TireSetCreateRequest,
    TireSetResponse,
    TireSetUpdateRequest,
)
from app.common.middleware import (
    verify_tire_set_access,
    verify_vehicle_access,
    verify_vehicle_view_access,
)
from app.db.database import get_db
from app.services.dto import ReplacementDTO, TireSetDTO, VehicleDTO
from app.services.tire_set_service import TireSetService

logger = logging.getLogger(__name__)


class TireSetHandler:
    """Хэндлер для операций с комплектами шин."""

    @staticmethod
    def _to_response(tire_set: TireSetDTO) -> TireSetResponse:
        """Преобразовать DTO комплекта в ответ."""
        return TireSetResponse(
            id=tire_set.id or 0,
            vehicle_id=tire_set.vehicle_id,
            name=tire_set.name,
            season=tire_set.season,  # type: ignore[arg-type]
            purchase_date=tire_set.purchase_date,
            purchase_price=tire_set.purchase_price,
            accumulated_km=tire_set.accumulated_km,
            installed_km=tire_set.installed_km,
            installed_date=tire_set.installed_date,
            is_installed=tire_set.is_installed,
            next_change_date=tire_set.next_change_date,
            status=tire_set.status,
            days_remaining=tire_set.days_remaining,
            total_km=tire_set.total_km,
            created_at=tire_set.created_at,
        )

    def _to_install_response(
        self,
        tire_set: TireSetDTO,
        replacement: ReplacementDTO,
        vehicle: VehicleDTO,
    ) -> TireInstallResponse:
        """Собрать ответ на переключение комплекта."""
        return TireInstallResponse(
            tire_set=self._to_response(tire_set),
            replacement=build_replacement_response(
                replacement,
                vehicle,
                is_latest=True,
                km_traveled=0,
            ),
        )

    async def get_tire_sets(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> list[TireSetResponse]:
        """Получить комплекты шин автомобиля."""
        try:
            service = TireSetService(db)
            tire_sets = service.get_by_vehicle(vehicle.id or 0, vehicle.current_km)
            return [self._to_response(item) for item in tire_sets]
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to get tire sets')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось получить комплекты шин',
            )

    async def create_tire_set(
        self,
        request: TireSetCreateRequest,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> TireSetResponse:
        """Создать комплект шин."""
        try:
            service = TireSetService(db)
            tire_set = service.create(vehicle.id or 0, request, vehicle)
            return self._to_response(tire_set)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to create tire set')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось создать комплект шин',
            )

    async def update_tire_set(
        self,
        request: TireSetUpdateRequest,
        db: Session = Depends(get_db),
        tire_set: TireSetDTO = Depends(verify_tire_set_access),
    ) -> TireSetResponse:
        """Обновить комплект шин."""
        try:
            service = TireSetService(db)
            updated = service.update(tire_set.id or 0, request)
            return self._to_response(updated)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to update tire set')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить комплект шин',
            )

    async def delete_tire_set(
        self,
        db: Session = Depends(get_db),
        tire_set: TireSetDTO = Depends(verify_tire_set_access),
    ) -> dict[str, str]:
        """Удалить комплект шин."""
        try:
            service = TireSetService(db)
            service.delete(tire_set.id or 0)
            return {'status': 'ok', 'message': f'Комплект шин {tire_set.id} удалён'}
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to delete tire set')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось удалить комплект шин',
            )

    async def install_tire_set(
        self,
        tire_set_id: int,
        request: TireInstallRequest | None = None,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> TireInstallResponse:
        """Переключить автомобиль на комплект шин."""
        try:
            service = TireSetService(db)
            tire_set, replacement = service.install(
                vehicle.id or 0,
                tire_set_id,
                request or TireInstallRequest(),
                vehicle,
            )
            return self._to_install_response(tire_set, replacement, vehicle)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to install tire set')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось переключить комплект шин',
            )


tire_set_handler = TireSetHandler()
