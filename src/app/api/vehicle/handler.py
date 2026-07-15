from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.api.vehicle.schema import (
    VehicleCreateRequest,
    VehicleResponse,
    UpdateKMRequest,
    UpdateVehicleData,
    VehicleUpdateIntervals,
    UpdateVehicleNotify,
)
from app.common.enums import ComponentType, StatusEnum
from app.common.component_config import COMPONENTS_CONFIG
from app.common.messages import ERROR_MESSAGES, SUCCESS_MESSAGES
from app.db.database import get_db
from app.db.models import UserDB
from app.auth.jwt import get_current_user
from app.services.replacement_service import ReplacementService
from app.services.vehicle_service import VehicleService
from app.services.dto import VehicleDTO, ReplacementDTO
from app.common.utils.calculator import StatusCalculator
from app.services.notification_service import check_vehicle_notifications


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
            vehicle_status=vehicle_status_value,
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
        replacements: list[ReplacementDTO],
    ) -> VehicleResponse:
        """Обогатить ответ остатками км до замен."""
        last_by_type: dict[ComponentType, ReplacementDTO] = {}
        for r in replacements:
            if r.component_type not in last_by_type or r.km_at_replacement > last_by_type[r.component_type].km_at_replacement:
                last_by_type[r.component_type] = r

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
        replacement_service: ReplacementService,
    ) -> VehicleResponse:
        """Построить ответ для автомобиля со статусом и остатками."""
        response = self._to_response(vehicle_dto)

        replacements = replacement_service.get_by_vehicle(vehicle_dto.id)
        response = self._enrich_with_remaining(response, vehicle_dto, replacements)

        worst_status = StatusCalculator.get_vehicle_status(vehicle_dto, replacements)
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

            if request.brand is not None:
                existing_dto.brand = request.brand
            if request.model is not None:
                existing_dto.model = request.model
            if request.plate_number is not None:
                existing_dto.plate_number = request.plate_number
            if request.year is not None:
                existing_dto.year = request.year
            if request.current_km is not None:
                existing_dto.current_km = request.current_km
            if request.intervals is not None:
                existing_dto.intervals.update(request.intervals)
            if request.notify_flags is not None:
                existing_dto.notify_flags.update(request.notify_flags)

            updated_dto = vehicle_service.update(existing_dto)

            if request.current_km is not None:
                check_vehicle_notifications(db, vehicle_id)

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

            check_vehicle_notifications(db, vehicle_id)

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
        """Обновить интервалы замен."""
        vehicle_service = VehicleService(db)
        try:
            existing_dto = self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            if request.intervals is not None:
                existing_dto.intervals.update(request.intervals)

            updated_dto = vehicle_service.update(existing_dto)
            return self._to_response(updated_dto)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to update intervals: {err}',
            )

    async def update_notify(
        self,
        vehicle_id: int,
        request: UpdateVehicleNotify,
        db: Session = Depends(get_db),
        current_user: UserDB = Depends(get_current_user),
    ) -> VehicleResponse:
        """Обновить настройки уведомлений для авто."""
        vehicle_service = VehicleService(db)
        try:
            existing_dto = self._get_vehicle_and_check_access(vehicle_id, current_user, vehicle_service)

            if request.notify_flags is not None:
                existing_dto.notify_flags.update(request.notify_flags)

            updated_dto = vehicle_service.update(existing_dto)
            return self._to_response(updated_dto)
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Failed to update notify settings: {err}',
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

            replacement_service.delete_by_vehicle(vehicle_id)
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
