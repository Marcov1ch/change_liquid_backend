from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.api.vehicle.schema import (
    VehicleRequest,
    VehicleResponse,
    UpdateKMRequest,
    UpdateVehicleData,
    VehicleUpdateIntervals,
)
from app.common.enums import StatusEnum
from app.common.liquid_config import LIQUIDS_CONFIG
from app.common.utils.templates.messages import ERROR_MESSAGES, SUCCESS_MESSAGES
from app.db.database import get_db
from app.db.models import UserDB
from app.auth.jwt import get_current_user
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.services.dto import VehicleDTO, ReplacementDTO
from app.common.utils.calculator import LiquidCalculator
from app.services.notification_service import NotificationService


class VehicleHandler:
    """Хэндлер для операций с автомобилем."""

    def _to_response(
        self,
        vehicle_dto: VehicleDTO,
        vehicle_status: str = StatusEnum.UNKNOWN.value,
    ) -> VehicleResponse:
        """Преобразование VehicleDTO в VehicleResponse."""
        return VehicleResponse(
            id=vehicle_dto.id,
            brand=vehicle_dto.brand,
            model=vehicle_dto.model,
            plate_number=vehicle_dto.plate_number,
            year=vehicle_dto.year,
            current_km=vehicle_dto.current_km,
            is_active=vehicle_dto.is_active,
            oil_interval_km=vehicle_dto.oil_interval_km,
            transmission_interval_km=vehicle_dto.transmission_interval_km,
            brake_interval_km=vehicle_dto.brake_interval_km,
            coolant_interval_km=vehicle_dto.coolant_interval_km,
            power_steering_interval_km=vehicle_dto.power_steering_interval_km,
            differential_oil_interval_km=vehicle_dto.differential_oil_interval_km,
            vehicle_status=vehicle_status,
            oil_notify_enabled=vehicle_dto.oil_notify_enabled,
            transmission_notify_enabled=vehicle_dto.transmission_notify_enabled,
            brake_notify_enabled=vehicle_dto.brake_notify_enabled,
            coolant_notify_enabled=vehicle_dto.coolant_notify_enabled,
            power_steering_notify_enabled=vehicle_dto.power_steering_notify_enabled,
            differential_oil_notify_enabled=vehicle_dto.differential_oil_notify_enabled,
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
            return max(0, next_km - current_km)  # type: ignore[no-any-return]
        return None

    def _enrich_with_remaining(
        self,
        response: VehicleResponse,
        vehicle_dto: VehicleDTO,
        replacement_service: ReplacementService,
    ) -> VehicleResponse:
        """Обогатить ответ остатками км до замен."""
        for config in LIQUIDS_CONFIG:
            last = replacement_service.get_last_for_vehicle_and_liquid(vehicle_dto.id, config.type)
            interval = getattr(vehicle_dto, config.interval_field)
            remaining = self._calc_remaining(last, interval, vehicle_dto.current_km)
            setattr(response, config.remaining_field, remaining)
        return response

    def _build_vehicle_response(
        self,
        vehicle_dto: VehicleDTO,
        replacement_service: ReplacementService,
    ) -> VehicleResponse:
        """Построить ответ для автомобиля со статусом и остатками."""
        response = self._to_response(vehicle_dto)
        response = self._enrich_with_remaining(response, vehicle_dto, replacement_service)

        # Получаем статус автомобиля
        replacements = replacement_service.get_by_vehicle(vehicle_dto.id)
        worst_status = LiquidCalculator.get_vehicle_status(vehicle_dto, replacements)
        response.vehicle_status = worst_status

        return response

    def _get_vehicle_and_check_access(
        self,
        vehicle_id: int,
        current_user: UserDB,
        vehicle_service: VehicleService,
    ) -> VehicleDTO:
        """Получить авто и проверить доступ."""
        existing_dto = vehicle_service.get_by_id(vehicle_id)
        if not existing_dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES['vehicle_not_found'].format(vehicle_id=vehicle_id),
            )
        if existing_dto.owner_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )
        return existing_dto

    async def get_vehicles(
        self,
        include_archived: bool = False,
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

        return [self._build_vehicle_response(v, replacement_service) for v in vehicles_dto]

    async def get_vehicle(
        self,
        vehicle_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> VehicleResponse:
        """Получить автомобиль по ID."""
        vehicle_service = VehicleService(db)
        replacement_service = ReplacementService(db)

        vehicle_dto = self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

        return self._build_vehicle_response(vehicle_dto, replacement_service)

    async def create_vehicle(
        self,
        request: VehicleRequest,
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
                    detail=ERROR_MESSAGES['plate_number_exists'].format(plate_number=request.plate_number),
                )

            vehicle_dto = vehicle_service.create(current_user.id, request)

            return self._to_response(vehicle_dto)
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to create vehicle: {err}',
            )

    async def update_vehicle(
        self,
        vehicle_id: int,
        request: UpdateVehicleData,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> VehicleResponse:
        """Обновить данные авто."""
        vehicle_service = VehicleService(db)
        try:
            existing_dto = self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            updated_data = request.model_dump(exclude_none=True)
            for field, value in updated_data.items():
                setattr(existing_dto, field, value)
            updated_dto = vehicle_service.update(existing_dto)

            return self._to_response(updated_dto)
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to update vehicle: {err}',
            )

    async def update_vehicle_km(
        self,
        vehicle_id: int,
        request: UpdateKMRequest,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> VehicleResponse:
        """Обновить пробег авто."""
        vehicle_service = VehicleService(db)
        try:
            self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            vehicle_dto = vehicle_service.update_km(
                vehicle_id=vehicle_id,
                new_km=request.new_km,
            )

            notification_service = NotificationService(db)
            notification_service.check_and_notify(vehicle_id)

            return self._to_response(vehicle_dto)
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to update km: {err}'
            )

    async def update_vehicle_intervals(
        self,
        vehicle_id: int,
        request: VehicleUpdateIntervals,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> VehicleResponse:
        """Обновить интервалы замены жидкостей."""
        vehicle_service = VehicleService(db)
        try:
            existing_dto = self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            updated_data = request.model_dump(exclude_none=True)
            for field, value in updated_data.items():
                setattr(existing_dto, field, value)
            updated_dto = vehicle_service.update(existing_dto)
            return self._to_response(updated_dto)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to update intervals: {err}',
            )

    async def delete_vehicle(
        self,
        vehicle_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> dict[str, str]:
        """Мягкое удаление авто (в архив)."""
        vehicle_service = VehicleService(db)
        try:
            self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            vehicle_service.delete(vehicle_id)
            return {
                'status': 'ok',
                'message': SUCCESS_MESSAGES['vehicle_deleted'].format(vehicle_id=vehicle_id),
            }
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to delete vehicle: {err}',
            )

    async def hard_delete_vehicle(
        self,
        vehicle_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> dict[str, str]:
        """Полное удаление авто из БД."""
        vehicle_service = VehicleService(db)
        replacement_service = ReplacementService(db)

        try:
            self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            replacements = replacement_service.get_by_vehicle(vehicle_id)
            for replacement in replacements:
                replacement_service.delete(replacement.id)
            vehicle_service.hard_delete(vehicle_id)

            return {
                'status': 'ok',
                'message': f'Vehicle {vehicle_id} and all its replacements have been permanently deleted',
            }
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to hard delete vehicle: {err}',
            )

    async def restore_vehicle(
        self,
        vehicle_id: int,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> VehicleResponse:
        """Восстановить авто из архива."""
        vehicle_service = VehicleService(db)
        try:
            existing_dto = self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            if existing_dto.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Vehicle is already active',
                )
            existing_dto.is_active = True
            updated_dto = vehicle_service.update(existing_dto)
            return self._to_response(updated_dto)
        except HTTPException:
            raise
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to restore vehicle: {err}',
            )


vehicle_handler = VehicleHandler()
