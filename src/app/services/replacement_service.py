from datetime import date
from sqlalchemy.orm import Session
from app.api.replacement.schema import ReplacementCreateRequest
from app.common.messages import ERROR_MESSAGES, VALIDATION_ERRORS
from app.common.models.replacement import Replacement
from app.common.enums import ComponentType
from app.common.utils.interval_utils import ComponentIntervalUtils
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import ReplacementDTO, VehicleDTO


class ReplacementService:
    """Класс для работы с заменами."""

    def __init__(self, db: Session):
        self.repository = ReplacementRepository(db)
        self.vehicle_repository = VehicleRepository(db)

    def create(
        self,
        vehicle_id: int,
        request: ReplacementCreateRequest,
    ) -> ReplacementDTO:
        """Создать запись о замене компонента."""
        vehicle_dto = self.vehicle_repository.find_active_by_id(vehicle_id)
        if not vehicle_dto:
            raise ValueError(ERROR_MESSAGES['vehicle_not_found'].format(vehicle_id=vehicle_id))

        self._validate_common(
            request.km_at_replacement,
            request.replacement_date,
        )
        self._validate_sequence(
            vehicle_id,
            request.component_type,
            request.km_at_replacement,
            request.replacement_date,
            exclude_id=None,
        )
        self._update_vehicle_km_if_needed(
            vehicle_dto,
            request.km_at_replacement,
        )

        interval_km = ComponentIntervalUtils.get_interval_for_component(vehicle_dto, request.component_type)

        replacement = Replacement(
            id=None,
            vehicle_id=vehicle_id,
            component_type=request.component_type,
            component_name=request.component_name,
            component_price=request.component_price,
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
        """Получить замену по id."""
        replacement = self.repository.find_by_id(replacement_id)
        return self._to_dto(replacement) if replacement else None

    def get_by_vehicle(
        self,
        vehicle_id: int,
    ) -> list[ReplacementDTO]:
        """Получить все замены для авто."""
        return [self._to_dto(r) for r in self.repository.find_by_vehicle_id(vehicle_id)]

    def get_by_vehicle_and_component(
        self,
        vehicle_id: int,
        component_type: ComponentType,
    ) -> list[ReplacementDTO]:
        """Получить замены для компонента автомобиля."""
        return [self._to_dto(r) for r in self.repository.find_by_vehicle_and_component(vehicle_id, component_type)]

    def get_last_for_vehicle_and_component(
        self,
        vehicle_id: int,
        component_type: ComponentType,
    ) -> ReplacementDTO | None:
        """Получить последнюю замену для компонента автомобиля."""
        replacement = self.repository.get_last_replacement(vehicle_id, component_type)
        return self._to_dto(replacement) if replacement else None

    def update(  # type: ignore[no-untyped-def]
        self,
        replacement_id: int,
        **kwargs,
    ) -> ReplacementDTO | None:
        """Обновить запись о замене."""
        replacement = self.repository.find_by_id(replacement_id)
        if not replacement:
            return None

        new_km = kwargs.get('km_at_replacement')
        new_date = kwargs.get('replacement_date')

        if new_km is not None:
            if new_km < 0:
                raise ValueError('Пробег не может быть отрицательным')

            vehicle_dto = self.vehicle_repository.find_active_by_id(replacement.vehicle_id)
            if vehicle_dto and new_km < vehicle_dto.current_km:
                raise ValueError(VALIDATION_ERRORS['km_less_than_current'].format(km=new_km, current_km=vehicle_dto.current_km))

            self._validate_sequence(
                replacement.vehicle_id,
                replacement.component_type,
                new_km,
                replacement.replacement_date,
                exclude_id=replacement_id,
            )

        if new_date is not None:
            if new_date > date.today():
                raise ValueError('Дата не может быть в будущем')
            self._validate_sequence(
                replacement.vehicle_id,
                replacement.component_type,
                replacement.km_at_replacement,
                new_date,
                exclude_id=replacement_id,
            )

        for key, value in kwargs.items():
            if value is not None and hasattr(replacement, key):
                setattr(replacement, key, value)

        vehicle_dto = self.vehicle_repository.find_active_by_id(replacement.vehicle_id)
        if vehicle_dto and replacement.km_at_replacement > vehicle_dto.current_km:
            vehicle_dto.current_km = replacement.km_at_replacement
            self.vehicle_repository.save(vehicle_dto)

        updated = self.repository.save(replacement)
        return self._to_dto(updated) if updated else None

    def delete(self, replacement_id: int) -> bool:
        """Удалить запись о замене."""
        return bool(self.repository.delete(replacement_id))

    def delete_by_vehicle(self, vehicle_id: int) -> int:
        """Удалить все замены для автомобиля."""
        return self.repository.delete_by_vehicle_id(vehicle_id)  # type: ignore[no-any-return]

    def _to_dto(self, replacement: Replacement) -> ReplacementDTO:
        """Преобразовать модель в DTO."""
        return ReplacementDTO(
            id=replacement.id,
            vehicle_id=replacement.vehicle_id,
            component_type=replacement.component_type,
            component_name=replacement.component_name,
            component_price=replacement.component_price,
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
        """Выполнить базовую валидацию пробега и даты."""
        if km < 0:
            raise ValueError(VALIDATION_ERRORS['negative_km'])
        if date_val > date.today():
            raise ValueError(VALIDATION_ERRORS['future_date'])

    def _validate_sequence(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        km: int,
        date_val: date,
        exclude_id: int | None,
    ) -> None:
        """Проверить, что новая замена не нарушает хронологию."""
        last = self.repository.get_last_replacement(vehicle_id, component_type)
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
        vehicle_dto: VehicleDTO,
        new_km: int,
    ) -> None:
        """Обновить пробег автомобиля, если новый пробег больше текущего."""
        if new_km > vehicle_dto.current_km:
            vehicle_dto.current_km = new_km
            self.vehicle_repository.save(vehicle_dto)
