import logging

from fastapi import HTTPException, status, Depends, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.vehicle.schema import (
    VehicleCreateRequest,
    VehicleResponse,
    UpdateKMRequest,
    UpdateVehicleData,
    VehicleUpdateIntervals,
    UpdateVehicleNotify,
    UpdateVehicleSizes,
)
from app.common.enums import StatusEnum
from app.common.component_config import COMPONENTS_CONFIG
from app.common.constants import MSG_PLATE_NUMBER_EXISTS
from app.common.exceptions import VehicleConflictError
from app.common.middleware import verify_vehicle_access, verify_vehicle_view_access
from app.db.database import get_db
from app.db.models import UserDB
from app.auth.jwt import get_current_user
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.services.dto import VehicleDTO, ReplacementDTO
from app.common.utils.calculator import StatusCalculator
from app.common.utils.interval_utils import get_last_per_type
from app.services.notification_service import check_vehicle_notifications_background


logger = logging.getLogger(__name__)


class VehicleHandler:
    """Хэндлер для операций с автомобилем."""

    def _to_response(
        self,
        vehicle_dto: VehicleDTO,
        vehicle_status: str = StatusEnum.UNKNOWN.value,
    ) -> VehicleResponse:
        """Преобразование VehicleDTO в VehicleResponse."""
        vehicle_status_value: str = vehicle_status
        return VehicleResponse(
            id=vehicle_dto.id,
            brand=vehicle_dto.brand,
            model=vehicle_dto.model,
            plate_number=vehicle_dto.plate_number,
            year=vehicle_dto.year,
            current_km=vehicle_dto.current_km,
            is_active=vehicle_dto.is_active,
            intervals=vehicle_dto.intervals.copy(),
            notify_flags=vehicle_dto.notify_flags.copy(),
            interval_months=vehicle_dto.interval_months.copy(),
            vehicle_status=vehicle_status_value,
            rims=[dict(r) for r in vehicle_dto.rims],
            tires=[dict(t) for t in vehicle_dto.tires],
        )

    def _calc_remaining(
        self,
        last_replacement: ReplacementDTO | None,
        interval_km: int,
        current_km: int,
    ) -> int | None:
        """Рассчитать остаток км до замены."""
        if last_replacement:
            next_km = last_replacement.km_at_replacement + interval_km
            return next_km - current_km  # type: ignore[no-any-return]
        return None

    def _enrich_with_remaining(
        self,
        response: VehicleResponse,
        vehicle_dto: VehicleDTO,
        replacements: list[ReplacementDTO],
    ) -> VehicleResponse:
        """Обогатить ответ остатками км до замен."""
        last_by_type = get_last_per_type(replacements)

        for config in COMPONENTS_CONFIG:
            last = last_by_type.get(config.type)
            interval = vehicle_dto.intervals.get(config.type.value)
            if interval is not None:
                remaining = self._calc_remaining(last, interval, vehicle_dto.current_km)
                response.km_remaining[config.type.value] = remaining
        return response

    def _build_vehicle_response(
        self,
        vehicle_dto: VehicleDTO,
        replacements: list[ReplacementDTO],
    ) -> VehicleResponse:
        """Построить ответ для автомобиля со статусом и остатками."""
        response = self._to_response(vehicle_dto)
        response = self._enrich_with_remaining(response, vehicle_dto, replacements)

        worst_status = StatusCalculator.get_vehicle_status(vehicle_dto, replacements)
        response.vehicle_status = worst_status

        return response

    async def get_vehicles(
        self,
        include_archived: bool = False,
        limit: int | None = Query(None, ge=1, le=1000),
        offset: int | None = Query(None, ge=0),
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> list[VehicleResponse]:
        """Получить автомобили (активные или все)."""
        vehicle_service = VehicleService(db)
        replacement_service = ReplacementService(db)

        if include_archived:
            vehicles_dto = vehicle_service.get_all_vehicles_by_owner(current_user.id)
        else:
            vehicles_dto = vehicle_service.get_all_active_by_owner(current_user.id)

        if offset is not None or limit is not None:
            start = offset or 0
            end = None if limit is None else start + limit
            vehicles_dto = vehicles_dto[start:end]

        vehicle_ids = [v.id for v in vehicles_dto]
        replacements_by_vehicle = replacement_service.get_by_vehicles(vehicle_ids) if vehicle_ids else {}

        return [
            self._build_vehicle_response(v, replacements_by_vehicle.get(v.id, []))
            for v in vehicles_dto
        ]

    async def get_vehicle(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> VehicleResponse:
        """Получить автомобиль по ID."""
        replacement_service = ReplacementService(db)

        replacements = replacement_service.get_by_vehicle(vehicle.id)
        return self._build_vehicle_response(vehicle, replacements)

    async def create_vehicle(
        self,
        request: VehicleCreateRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> VehicleResponse:
        """Создать авто."""
        vehicle_service = VehicleService(db)
        try:
            existing = vehicle_service.get_by_plate_number(request.plate_number)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=MSG_PLATE_NUMBER_EXISTS.format(plate_number=request.plate_number),
                )

            vehicle_dto = vehicle_service.create(current_user.id, request)

            return self._to_response(vehicle_dto)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to create vehicle')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось создать автомобиль',
            )

    @staticmethod
    def _changed_fields(request: BaseModel) -> dict:
        """Выделить поля, переданные в запросе (без явных None верхнего уровня)."""
        return {
            key: value
            for key, value in request.model_dump(exclude_unset=True).items()
            if value is not None
        }

    async def update_vehicle(
        self,
        request: UpdateVehicleData,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> VehicleResponse:
        """Обновить данные авто."""
        vehicle_service = VehicleService(db)
        payload = self._changed_fields(request)
        try:
            updated_dto = vehicle_service.partial_update(vehicle, payload)

            if 'interval_months' in payload:
                replacement_service = ReplacementService(db)
                replacement_service.reset_date_notify_flags(vehicle.id)

            if 'current_km' in payload:
                background_tasks.add_task(
                    check_vehicle_notifications_background,
                    vehicle.id,
                )

            return self._to_response(updated_dto)
        except VehicleConflictError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(err),
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except IntegrityError:
            db.rollback()
            detail = (
                MSG_PLATE_NUMBER_EXISTS.format(plate_number=payload['plate_number'])
                if payload.get('plate_number') is not None
                else 'Автомобиль с такими данными уже существует'
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )
        except Exception:
            logger.exception('Failed to update vehicle')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить автомобиль',
            )

    async def update_vehicle_km(
        self,
        request: UpdateKMRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> VehicleResponse:
        """Обновить пробег авто."""
        vehicle_service = VehicleService(db)
        try:
            vehicle_dto = vehicle_service.update_km(
                vehicle_id=vehicle.id,
                new_km=request.new_km,
            )

            background_tasks.add_task(
                check_vehicle_notifications_background,
                vehicle.id,
            )

            return self._to_response(vehicle_dto)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to update vehicle km')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить пробег'
            )

    async def update_vehicle_intervals(
        self,
        request: VehicleUpdateIntervals,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> VehicleResponse:
        """Обновить интервалы замен."""
        vehicle_service = VehicleService(db)
        payload = self._changed_fields(request)
        try:
            updated_dto = vehicle_service.partial_update(vehicle, payload)
            return self._to_response(updated_dto)
        except VehicleConflictError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(err),
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to update vehicle intervals')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить интервалы',
            )

    async def update_notify(
        self,
        request: UpdateVehicleNotify,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> VehicleResponse:
        """Обновить настройки уведомлений для авто."""
        vehicle_service = VehicleService(db)
        payload = self._changed_fields(request)
        try:
            updated_dto = vehicle_service.partial_update(vehicle, payload)
            return self._to_response(updated_dto)
        except VehicleConflictError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(err),
            )
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to update vehicle notify settings')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить настройки уведомлений',
            )

    async def update_sizes(
        self,
        request: UpdateVehicleSizes,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> VehicleResponse:
        """Обновить списки допустимых дисков и шин."""
        vehicle_service = VehicleService(db)
        try:
            rims = [r.model_dump() for r in request.rims]
            tires = [t.model_dump() for t in request.tires]

            updated_dto = vehicle_service.repository.replace_sizes(vehicle.id, rims, tires)
            if updated_dto is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Автомобиль не найден',
                )

            return self._to_response(updated_dto)
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to update vehicle sizes')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить размеры дисков и шин',
            )

    async def delete_vehicle(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_access),
    ) -> dict[str, str]:
        """Мягкое удаление авто (в архив)."""
        vehicle_service = VehicleService(db)
        try:
            vehicle_service.delete(vehicle.id)
            return {
                'status': 'ok',
                'message': f'Автомобиль {vehicle.id} успешно удален',
            }
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to delete vehicle')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось удалить автомобиль',
            )

    async def hard_delete_vehicle(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> dict[str, str]:
        """Полное удаление авто из БД."""
        vehicle_service = VehicleService(db)
        replacement_service = ReplacementService(db)

        try:
            replacement_service.delete_by_vehicle(vehicle.id, commit=False)
            vehicle_service.hard_delete(vehicle.id, commit=False)
            db.commit()

            return {
                'status': 'ok',
                'message': f'Автомобиль {vehicle.id} и все его замены полностью удалены',
            }
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception('Failed to hard delete vehicle')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось полностью удалить автомобиль',
            )

    async def restore_vehicle(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> VehicleResponse:
        """Восстановить авто из архива."""
        vehicle_service = VehicleService(db)
        try:
            if vehicle.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Автомобиль уже активен',
                )
            vehicle.is_active = True
            updated_dto = vehicle_service.update(vehicle)
            return self._to_response(updated_dto)
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to restore vehicle')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось восстановить автомобиль',
            )


vehicle_handler = VehicleHandler()
