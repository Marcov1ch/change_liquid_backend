import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.replacement.mapper import build_replacement_response
from app.api.share.schema import (
    PublicFuelRecordResponse,
    PublicOtherExpenseResponse,
    PublicRepairResponse,
    PublicReplacementResponse,
    PublicVehicleResponse,
    ShareLinkResponse,
)
from app.common.config import build_register_url, build_share_url
from app.common.middleware import verify_vehicle_view_access
from app.common.utils.calculator import StatusCalculator
from app.db.database import get_db
from app.services.dto import VehicleDTO
from app.services.fuel_record_service import FuelRecordService
from app.services.other_expense_service import OtherExpenseService
from app.services.repair_service import RepairService
from app.services.replacement_service import ReplacementService
from app.services.share_service import VehicleShareService

logger = logging.getLogger(__name__)

_MSG_SHARE_NOT_FOUND = 'Ссылка не найдена или отключена'


class ShareHandler:
    """Хэндлер публичного шаринга авто."""

    @staticmethod
    def _link_response(token: str | None) -> ShareLinkResponse:
        return ShareLinkResponse(
            enabled=token is not None,
            token=token,
            share_url=build_share_url(token) if token else None,
            register_url=build_register_url(),
        )

    async def get_share(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> ShareLinkResponse:
        """Получить состояние публичной ссылки."""
        share_service = VehicleShareService(db)
        return self._link_response(share_service.get_token(vehicle.id))

    async def enable_share(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> ShareLinkResponse:
        """Включить публичный доступ и вернуть ссылку."""
        share_service = VehicleShareService(db)

        try:
            token = share_service.enable(vehicle.id)
            return self._link_response(token)
        except Exception:
            logger.exception('Failed to enable vehicle share')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось включить публичный доступ',
            )

    async def rotate_share(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> ShareLinkResponse:
        """Перевыпустить публичную ссылку."""
        share_service = VehicleShareService(db)

        try:
            token = share_service.rotate(vehicle.id)
            return self._link_response(token)
        except Exception:
            logger.exception('Failed to rotate vehicle share')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось обновить публичную ссылку',
            )

    async def disable_share(
        self,
        db: Session = Depends(get_db),
        vehicle: VehicleDTO = Depends(verify_vehicle_view_access),
    ) -> ShareLinkResponse:
        """Отключить публичный доступ."""
        share_service = VehicleShareService(db)

        try:
            share_service.disable(vehicle.id)
            return self._link_response(None)
        except Exception:
            logger.exception('Failed to disable vehicle share')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось отключить публичный доступ',
            )

    async def get_public_vehicle(
        self,
        token: str,
        db: Session = Depends(get_db),
    ) -> PublicVehicleResponse:
        """Получить публичный профиль авто по токену."""
        share_service = VehicleShareService(db)

        try:
            vehicle = share_service.find_by_token(token)
            if not vehicle:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=_MSG_SHARE_NOT_FOUND,
                )

            replacement_service = ReplacementService(db)
            replacements = replacement_service.get_by_vehicle(vehicle.id)
            latest_ids = replacement_service.get_latest_replacement_ids(vehicle.id)
            km_traveled = replacement_service.get_tire_km_traveled(vehicle.id, vehicle.current_km)

            public_replacements = [
                PublicReplacementResponse(
                    **build_replacement_response(
                        replacement,
                        vehicle,
                        is_latest=replacement.id in latest_ids,
                        km_traveled=km_traveled.get(replacement.id or 0),
                    ).model_dump(exclude={'vehicle_id'}),
                )
                for replacement in replacements
            ]

            other_expense_service = OtherExpenseService(db)
            public_other_expenses = [
                PublicOtherExpenseResponse(
                    id=expense.id,
                    name=expense.name,
                    expense_date=expense.expense_date,
                    amount=expense.amount,
                )
                for expense in other_expense_service.get_by_vehicle(vehicle.id)
            ]

            fuel_record_service = FuelRecordService(db)
            public_fuel_records = [
                PublicFuelRecordResponse(
                    id=record.id,
                    fuel_date=record.fuel_date,
                    km_at_fuel=record.km_at_fuel,
                    liters=record.liters,
                    total_cost=record.total_cost,
                    consumption_l_per_100km=record.consumption_l_per_100km,
                )
                for record in fuel_record_service.get_by_vehicle(vehicle.id)
            ]

            repair_service = RepairService(db)
            public_repairs = [
                PublicRepairResponse(
                    id=repair.id,
                    repair_date=repair.repair_date,
                    km_at_repair=repair.km_at_repair,
                    description=repair.description,
                    work_cost=repair.work_cost,
                    parts_cost=repair.parts_cost,
                    component_types=repair.component_types,
                )
                for repair in repair_service.get_by_vehicle(vehicle.id)
            ]

            return PublicVehicleResponse(
                brand=vehicle.brand,
                model=vehicle.model,
                plate_number=vehicle.plate_number,
                year=vehicle.year,
                current_km=vehicle.current_km,
                vehicle_status=StatusCalculator.get_vehicle_status(vehicle, replacements),
                replacements=public_replacements,
                other_expenses=public_other_expenses,
                repairs=public_repairs,
                fuel_records=public_fuel_records,
                register_url=build_register_url(),
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception('Failed to get public vehicle')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Не удалось получить данные автомобиля',
            )


share_handler = ShareHandler()
