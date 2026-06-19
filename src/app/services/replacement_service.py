from datetime import date
from sqlalchemy.orm import Session
from app.api.liquid.schema import LiquidReplacementRequest
from app.common.messages import ERROR_MESSAGES, VALIDATION_ERRORS
from app.common.models.liquid import Liquid
from app.common.enums import LiquidType
from app.common.models.vehicle import Vehicle
from app.common.utils.interval_utils import IntervalUtils
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import ReplacementDTO


class ReplacementService:
    """Сервис для работы с заменами жидкостей."""

    def __init__(self, db: Session):
        self.repository = ReplacementRepository(db)
        self.vehicle_repository = VehicleRepository(db)

    def create(
        self,
        vehicle_id: int,
        request: LiquidReplacementRequest,
    ) -> ReplacementDTO:
        """Создать запись о замене."""
        vehicle = self.vehicle_repository.find_active_by_id(vehicle_id)
        if not vehicle:
            raise ValueError(ERROR_MESSAGES['vehicle_not_found'].format(vehicle_id=vehicle_id))

        self._validate_common(
            request.km_at_replacement,
            request.replacement_date,
        )
        self._validate_sequence(
            vehicle_id,
            request.liquid_type,
            request.km_at_replacement,
            request.replacement_date,
        )  # type: ignore[call-arg]
        self._update_vehicle_km_if_needed(
            vehicle,
            request.km_at_replacement,
        )

        interval_km = IntervalUtils.get_interval_for_liquid(vehicle, request.liquid_type)

        replacement = Liquid(
            id=None,
            vehicle_id=vehicle_id,
            liquid_type=request.liquid_type,
            liquid_name=request.liquid_name,
            liquid_price=request.liquid_price,
            work_price=request.work_price,
            replacement_date=request.replacement_date,
            km_at_replacement=request.km_at_replacement,
            interval_km=interval_km,
        )

        saved = self.repository.save(replacement)
        return self._to_dto(saved)

    def get_by_id(
        self,
        replacement_id: int,
    ) -> ReplacementDTO | None:
        """Получить запись о замене по ID."""
        replacement = self.repository.find_by_id(replacement_id)
        return self._to_dto(replacement) if replacement else None

    def get_by_vehicle(
        self,
        vehicle_id: int,
    ) -> list[ReplacementDTO]:
        """Получить запись о замене по авто."""
        return [self._to_dto(r) for r in self.repository.find_by_vehicle_id(vehicle_id)]

    def get_by_vehicle_and_liquid(
        self,
        vehicle_id: int,
        liquid_type: LiquidType,
    ) -> list[ReplacementDTO]:
        """Получить записи о заменах по авто и жидкости."""
        return [self._to_dto(r) for r in self.repository.find_by_vehicle_and_liquid(vehicle_id, liquid_type)]

    def get_last_for_vehicle_and_liquid(
        self,
        vehicle_id: int,
        liquid_type: LiquidType,
    ) -> ReplacementDTO | None:
        """Получить последнюю замену по авто и жидкости."""
        replacement = self.repository.get_last_replacement(vehicle_id, liquid_type)
        return self._to_dto(replacement) if replacement else None

    def update(  # type: ignore[no-untyped-def]
        self,
        replacement_id: int,
        **kwargs,
    ) -> ReplacementDTO | None:
        """Обновить данные о замене."""
        replacement = self.repository.find_by_id(replacement_id)
        if not replacement:
            return None

        new_km = kwargs.get('km_at_replacement')
        new_date = kwargs.get('replacement_date')

        if new_km is not None:
            if new_km < 0:
                raise ValueError('Пробег не может быть отрицательным')

            vehicle = self.vehicle_repository.find_active_by_id(replacement.vehicle_id)
            if vehicle and new_km < vehicle.current_km:
                raise ValueError(VALIDATION_ERRORS['km_less_than_current'].format(km=new_km, current_km=vehicle.current_km))

            self._validate_sequence(
                replacement.vehicle_id,
                replacement.liquid_type,
                new_km,
                replacement.replacement_date,
                exclude_id=replacement_id,
            )

        if new_date is not None:
            if new_date > date.today():
                raise ValueError('Дата не может быть в будущем')
            self._validate_sequence(
                replacement.vehicle_id,
                replacement.liquid_type,
                replacement.km_at_replacement,
                new_date,
                exclude_id=replacement_id,
            )

        for key, value in kwargs.items():
            if value is not None and hasattr(replacement, key):
                setattr(replacement, key, value)

        vehicle = self.vehicle_repository.find_active_by_id(replacement.vehicle_id)
        if vehicle and replacement.km_at_replacement > vehicle.current_km:
            vehicle.current_km = replacement.km_at_replacement
            self.vehicle_repository.save(vehicle)

        updated = self.repository.save(replacement)
        return self._to_dto(updated) if updated else None

    def delete(self, replacement_id: int) -> bool:
        """Удалить запись о замене."""
        return bool(self.repository.delete(replacement_id))

    def _to_dto(self, replacement: Liquid) -> ReplacementDTO:
        return ReplacementDTO(
            id=replacement.id,
            vehicle_id=replacement.vehicle_id,
            liquid_type=replacement.liquid_type,
            liquid_name=replacement.liquid_name,
            liquid_price=replacement.liquid_price,
            work_price=replacement.work_price,
            replacement_date=replacement.replacement_date,
            km_at_replacement=replacement.km_at_replacement,
            interval_km=replacement.interval_km,
        )

    def _validate_common(
        self,
        km: int,
        date_val: date,
    ) -> None:
        """Общая валидация пробега и даты."""
        if km < 0:
            raise ValueError(VALIDATION_ERRORS['negative_km'])
        if date_val > date.today():
            raise ValueError(VALIDATION_ERRORS['future_date'])

    def _validate_sequence(
        self,
        vehicle_id: int,
        liquid_type: LiquidType,
        km: int,
        date_val: date,
        exclude_id: int | None,
    ) -> None:
        """Проверить последовательность замен (пробег и дата должны увеличиваться)."""
        last = self.repository.get_last_replacement(vehicle_id, liquid_type)
        if not last or (exclude_id and last.id == exclude_id):
            return

        if km < last.km_at_replacement:
            raise ValueError(
                VALIDATION_ERRORS['km_less_than_previous'].format(km=km, previous_km=last.km_at_replacement))
        if date_val < last.replacement_date:
            raise ValueError(
                VALIDATION_ERRORS['date_less_than_previous'].format(date=date_val, previous_date=last.replacement_date))

    def _update_vehicle_km_if_needed(
        self,
        vehicle: Vehicle,
        new_km: int,
    ) -> None:
        """Обновить пробег авто если новый пробег больше."""
        if new_km > vehicle.current_km:
            vehicle.current_km = new_km
            self.vehicle_repository.save(vehicle)
