from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.api.replacement.schema import (
    ReplacementCreateRequest,
    UpdateReplacementRequest,
)
from app.common.enums import (
    ComponentType,
    DATE_BASED_COMPONENT_TYPES,
    DATE_ONLY_COMPONENT_TYPES,
    TireEventType,
)
from app.common.utils.interval_utils import ComponentIntervalUtils, add_months
from app.repository.repair_repository import RepairRepository
from app.repository.replacement_repository import ReplacementRepository
from app.repository.tire_set_repository import TireSetRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import ReplacementDTO, VehicleDTO

_MSG_VEHICLE_NOT_FOUND = 'Автомобиль с ID {vehicle_id} не найден'
_MSG_NEGATIVE_KM = 'Пробег не может быть отрицательным'
_MSG_FUTURE_DATE = 'Дата замены не может быть позже сегодняшнего дня'
_MSG_KM_LESS_THAN_PREVIOUS = 'Пробег ({km}) не может быть меньше предыдущей замены ({previous_km})'
_MSG_DATE_LESS_THAN_PREVIOUS = 'Дата ({date}) не может быть раньше предыдущей замены ({previous_date})'
_MSG_KM_GREATER_THAN_NEXT = 'Пробег ({km}) не может быть больше следующей замены ({next_km})'
_MSG_DATE_GREATER_THAN_NEXT = 'Дата ({date}) не может быть позже следующей замены ({next_date})'
_MSG_DUPLICATE_REPLACEMENT = 'Замена с текущим пробегом уже существует'
_MSG_INSURANCE_DATE_REQUIRED = 'Необходимо указать дату окончания'
_MSG_DATE_END_BEFORE_START = 'Дата окончания не может быть раньше даты начала'
_MSG_REPAIR_COST_CONFLICT = 'Нельзя указать стоимость: компонент входит в ремонт от {date}'
_MSG_TIRE_PURCHASE_IMMUTABLE = 'Покупка комплекта шин изменяется через настройки комплекта'
_MSG_TIRE_CURRENT_INSTALL_DELETE = (
    'Нельзя удалить запись установки текущего комплекта. '
    'Сначала переключитесь на другой комплект.'
)

REPAIR_PLACEHOLDER_NAME = 'ВНЕСИТЕ ИЗМЕНЕНИЕ'


@dataclass
class _ReplacementUpdate:
    """Итоговые значения замены после частичного обновления."""
    component_name: str | None
    component_price: int | None
    work_price: int | None
    replacement_date: date
    km_at_replacement: int
    next_change_date: date | None
    reset_date_notify: bool


class ReplacementService:
    """Класс для работы с заменами."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ReplacementRepository(db)
        self.vehicle_repository = VehicleRepository(db)
        self.repair_repository = RepairRepository(db)

    def _resolve_intervals(
        self,
        vehicle_dto: VehicleDTO,
        component_type: ComponentType,
        replacement_date: date,
        is_date_based: bool,
        next_change_date: date | None = None,
    ) -> tuple[int, int | None, date | None]:
        """Рассчитать интервалы и дату следующей замены для компонента."""
        if is_date_based:
            return 0, None, next_change_date

        interval_km = ComponentIntervalUtils.get_interval_for_component(
            vehicle_dto,
            component_type,
        )
        interval_months = ComponentIntervalUtils.get_interval_months_for_component(
            vehicle_dto,
            component_type,
        )
        if interval_months is not None:
            next_change_date = add_months(replacement_date, interval_months)

        return interval_km, interval_months, next_change_date

    def create(
        self,
        vehicle_id: int,
        request: ReplacementCreateRequest,
        vehicle_dto: VehicleDTO | None = None,
        commit: bool = True,
        tire_set_id: int | None = None,
        tire_event_type: str | None = None,
    ) -> ReplacementDTO:
        """Создать запись о замене компонента."""
        if vehicle_dto is None:
            vehicle_dto = self.vehicle_repository.find_active_by_id(vehicle_id)
        if not vehicle_dto:
            raise ValueError(_MSG_VEHICLE_NOT_FOUND.format(vehicle_id=vehicle_id))

        self._validate_repair_cost_conflict(
            vehicle_id,
            request.component_type,
            request.replacement_date,
            request.component_price,
            request.work_price,
        )

        is_date_based = request.component_type in DATE_BASED_COMPONENT_TYPES
        is_date_only = request.component_type in DATE_ONLY_COMPONENT_TYPES

        if is_date_only:
            if request.next_change_date is None:
                raise ValueError(_MSG_INSURANCE_DATE_REQUIRED)
            if request.next_change_date < request.replacement_date:
                raise ValueError(_MSG_DATE_END_BEFORE_START)

        if not is_date_based:
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
            self._validate_no_duplicate(
                vehicle_id,
                request.component_type,
                request.km_at_replacement,
            )

        km_at_replacement = 0 if is_date_only else request.km_at_replacement
        self._update_vehicle_km_if_needed(
            vehicle_dto,
            km_at_replacement,
            commit,
        )

        interval_km, interval_months, next_change_date = self._resolve_intervals(
            vehicle_dto,
            request.component_type,
            request.replacement_date,
            is_date_based,
            request.next_change_date,
        )

        replacement = ReplacementDTO(
            id=None,
            vehicle_id=vehicle_id,
            component_type=request.component_type,
            component_name=request.component_name,
            component_price=request.component_price,
            work_price=None if is_date_only else request.work_price,
            replacement_date=request.replacement_date,
            km_at_replacement=km_at_replacement,
            interval_km=interval_km,
            interval_months=interval_months,
            next_change_date=next_change_date,
            tire_set_id=tire_set_id,
            tire_event_type=tire_event_type,
        )

        return self.repository.save(replacement, commit=commit)

    def get_by_id(
        self,
        replacement_id: int,
    ) -> ReplacementDTO | None:
        """Получить замену по id."""
        return self.repository.find_by_id(replacement_id)

    def get_by_vehicle(
        self,
        vehicle_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ReplacementDTO]:
        """Получить замены для авто (с опциональной пагинацией)."""
        return self.repository.find_by_vehicle_id(vehicle_id, limit=limit, offset=offset)  # type: ignore[no-any-return]

    def get_latest_replacement_ids(self, vehicle_id: int) -> set[int]:
        """Получить id последних замен по каждому типу компонента авто."""
        return self.repository.get_latest_replacement_ids(vehicle_id)  # type: ignore[no-any-return]

    def get_tire_km_traveled(
        self,
        vehicle_id: int,
        current_km: int,
    ) -> dict[int, int]:
        """Рассчитать пройденный пробег для каждой записи о замене шин."""
        tires = [
            tire
            for tire in self.repository.find_by_vehicle_and_component(
                vehicle_id, ComponentType.TIRE_CHANGE,
            )
            if tire.tire_event_type != TireEventType.PURCHASE.value
        ]
        ordered = sorted(
            tires,
            key=lambda r: (r.km_at_replacement, r.replacement_date, r.id or 0),
        )

        traveled: dict[int, int] = {}
        for index, tire in enumerate(ordered):
            if tire.id is None:
                continue
            end_km = (
                ordered[index + 1].km_at_replacement
                if index + 1 < len(ordered)
                else current_km
            )
            traveled[tire.id] = max(0, end_km - tire.km_at_replacement)
        return traveled

    def get_by_vehicles(
        self,
        vehicle_ids: list[int],
    ) -> dict[int, list[ReplacementDTO]]:
        """Получить все замены для списка авто, сгруппированные по vehicle_id."""
        replacements = self.repository.find_by_vehicle_ids(vehicle_ids)
        grouped: dict[int, list[ReplacementDTO]] = {}
        for r in replacements:
            grouped.setdefault(r.vehicle_id, []).append(r)
        return grouped

    def get_by_vehicle_and_component(
        self,
        vehicle_id: int,
        component_type: ComponentType,
    ) -> list[ReplacementDTO]:
        """Получить замены для компонента автомобиля."""
        return self.repository.find_by_vehicle_and_component(vehicle_id, component_type)  # type: ignore[no-any-return]

    def get_last_for_vehicle_and_component(
        self,
        vehicle_id: int,
        component_type: ComponentType,
    ) -> ReplacementDTO | None:
        """Получить последнюю замену для компонента автомобиля."""
        return self.repository.get_last_replacement(vehicle_id, component_type)

    def update(
        self,
        replacement_id: int,
        request: UpdateReplacementRequest,
        commit: bool = True,
    ) -> ReplacementDTO | None:
        """Обновить запись о замене."""
        replacement = self.repository.find_by_id(replacement_id)
        if not replacement:
            return None
        if replacement.tire_event_type == TireEventType.PURCHASE.value:
            raise ValueError(_MSG_TIRE_PURCHASE_IMMUTABLE)

        vehicle_dto = self.vehicle_repository.find_active_by_id(replacement.vehicle_id)
        update = self._resolve_update(replacement, request, vehicle_dto)
        self._validate_update(replacement, update)
        return self._apply_update(replacement, update, vehicle_dto, commit)

    def _resolve_update(
        self,
        replacement: ReplacementDTO,
        request: UpdateReplacementRequest,
        vehicle_dto: VehicleDTO | None,
    ) -> _ReplacementUpdate:
        """Собрать итоговые значения замены из запроса и текущей записи."""
        is_date_based = replacement.component_type in DATE_BASED_COMPONENT_TYPES
        is_date_only = replacement.component_type in DATE_ONLY_COMPONENT_TYPES

        replacement_date = (
            request.replacement_date
            if request.replacement_date is not None
            else replacement.replacement_date
        )
        component_price = (
            request.component_price
            if request.component_price is not None
            else replacement.component_price
        )

        if is_date_only:
            work_price = replacement.work_price
            km_at_replacement = replacement.km_at_replacement
        else:
            work_price = (
                request.work_price
                if request.work_price is not None
                else replacement.work_price
            )
            km_at_replacement = (
                request.km_at_replacement
                if request.km_at_replacement is not None
                else replacement.km_at_replacement
            )

        next_change_date, reset_date_notify = self._resolve_next_change_date(
            replacement,
            request,
            vehicle_dto,
            replacement_date,
            is_date_based,
            is_date_only,
        )

        return _ReplacementUpdate(
            component_name=request.component_name,
            component_price=component_price,
            work_price=work_price,
            replacement_date=replacement_date,
            km_at_replacement=km_at_replacement,
            next_change_date=next_change_date,
            reset_date_notify=reset_date_notify,
        )

    def _resolve_next_change_date(
        self,
        replacement: ReplacementDTO,
        request: UpdateReplacementRequest,
        vehicle_dto: VehicleDTO | None,
        replacement_date: date,
        is_date_based: bool,
        is_date_only: bool,
    ) -> tuple[date | None, bool]:
        """Определить дату следующей замены и необходимость сброса date-флагов."""
        next_change_date = (
            request.next_change_date
            if request.next_change_date is not None
            else replacement.next_change_date
        )

        if is_date_only:
            reset = (
                request.replacement_date is not None
                and request.replacement_date != replacement.replacement_date
            ) or (
                request.next_change_date is not None
                and request.next_change_date != replacement.next_change_date
            )
            return next_change_date, reset

        if is_date_based:
            reset = (
                request.next_change_date is not None
                and request.next_change_date != replacement.next_change_date
            )
            return next_change_date, reset

        if vehicle_dto is not None:
            next_change_date = ComponentIntervalUtils.get_next_change_date(
                vehicle_dto,
                replacement.component_type,
                replacement_date,
            )
            return next_change_date, next_change_date != replacement.next_change_date

        return next_change_date, False

    def _validate_update(
        self,
        replacement: ReplacementDTO,
        update: _ReplacementUpdate,
    ) -> None:
        """Проверить итоговые значения обновлённой замены."""
        is_date_based = replacement.component_type in DATE_BASED_COMPONENT_TYPES
        is_date_only = replacement.component_type in DATE_ONLY_COMPONENT_TYPES

        self._validate_repair_cost_conflict(
            replacement.vehicle_id,
            replacement.component_type,
            update.replacement_date,
            update.component_price,
            update.work_price,
        )

        if is_date_only:
            if (
                update.next_change_date is not None
                and update.next_change_date < update.replacement_date
            ):
                raise ValueError(_MSG_DATE_END_BEFORE_START)

        if update.km_at_replacement < 0:
            raise ValueError(_MSG_NEGATIVE_KM)
        if update.replacement_date > date.today():
            raise ValueError(_MSG_FUTURE_DATE)

        if not is_date_based:
            self._validate_sequence(
                replacement.vehicle_id,
                replacement.component_type,
                update.km_at_replacement,
                update.replacement_date,
                exclude_id=replacement.id,
            )

    def _apply_update(
        self,
        replacement: ReplacementDTO,
        update: _ReplacementUpdate,
        vehicle_dto: VehicleDTO | None,
        commit: bool,
    ) -> ReplacementDTO:
        """Записать итоговые значения и сохранить замену."""
        is_date_only = replacement.component_type in DATE_ONLY_COMPONENT_TYPES

        if update.component_name is not None:
            replacement.component_name = update.component_name
        if update.component_price is not None:
            replacement.component_price = update.component_price
        if not is_date_only:
            replacement.work_price = update.work_price
            replacement.km_at_replacement = update.km_at_replacement

        replacement.replacement_date = update.replacement_date
        replacement.next_change_date = update.next_change_date

        if vehicle_dto and replacement.km_at_replacement > vehicle_dto.current_km:
            vehicle_dto.current_km = replacement.km_at_replacement
            self.vehicle_repository.save(vehicle_dto, commit=commit)

        updated = self.repository.save(replacement, commit=commit)
        if update.reset_date_notify and replacement.id is not None:
            self.repository.update_date_notify_tracking(
                replacement.id,
                date_warning_notified=False,
                date_overdue_notified=False,
            )
        return updated

    def delete(self, replacement_id: int, commit: bool = True) -> bool:
        """Удалить запись о замене."""
        replacement = self.repository.find_by_id(replacement_id)
        if replacement and self._is_current_tire_install(replacement):
            raise ValueError(_MSG_TIRE_CURRENT_INSTALL_DELETE)
        if (
            replacement
            and replacement.tire_event_type == TireEventType.PURCHASE.value
            and replacement.tire_set_id is not None
        ):
            self._clear_tire_set_purchase(replacement.tire_set_id, commit=False)

        deleted = self.repository.delete(replacement_id, commit=False)
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return bool(deleted)

    def _is_current_tire_install(self, replacement: ReplacementDTO) -> bool:
        """Проверить, является ли запись текущей установкой комплекта."""
        if replacement.tire_event_type != TireEventType.INSTALL.value:
            return False
        if replacement.tire_set_id is None:
            return False
        tire_set = TireSetRepository(self.db).find_by_id(replacement.tire_set_id)
        if tire_set is None or not tire_set.is_installed:
            return False
        last_install = self.repository.get_last_install_for_tire_set(replacement.tire_set_id)
        return last_install is not None and last_install.id == replacement.id

    def _clear_tire_set_purchase(self, tire_set_id: int, commit: bool = False) -> None:
        """Очистить данные покупки комплекта при удалении её записи из истории."""
        tire_set_repository = TireSetRepository(self.db)
        tire_set = tire_set_repository.find_by_id(tire_set_id)
        if not tire_set:
            return
        tire_set.purchase_price = None
        tire_set.purchase_date = None
        tire_set_repository.save(tire_set, commit=commit)

    def delete_by_vehicle(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все замены для автомобиля."""
        return self.repository.delete_by_vehicle_id(vehicle_id, commit)  # type: ignore[no-any-return]

    def reset_date_notify_flags(self, vehicle_id: int) -> int:
        """Сбросить флаги date-уведомлений для non-tire замен автомобиля."""
        return self.repository.reset_date_notify_flags(vehicle_id)  # type: ignore[no-any-return]

    def create_repair_placeholder(
        self,
        vehicle_dto: VehicleDTO,
        component_type: ComponentType,
        replacement_date: date,
        km_at_replacement: int,
        source_repair_id: int,
        commit: bool = True,
    ) -> ReplacementDTO:
        """Создать служебную замену для компонента ремонта без проверки хронологии."""
        if component_type in DATE_BASED_COMPONENT_TYPES:
            raise ValueError('Для этого компонента нельзя создать замену из ремонта')
        if vehicle_dto.id is None:
            raise ValueError(_MSG_VEHICLE_NOT_FOUND.format(vehicle_id='?'))

        self._validate_common(km_at_replacement, replacement_date)

        interval_km, interval_months, next_change_date = self._resolve_intervals(
            vehicle_dto,
            component_type,
            replacement_date,
            is_date_based=False,
        )

        replacement = ReplacementDTO(
            id=None,
            vehicle_id=vehicle_dto.id,
            component_type=component_type,
            component_name=REPAIR_PLACEHOLDER_NAME,
            component_price=0,
            work_price=0,
            replacement_date=replacement_date,
            km_at_replacement=km_at_replacement,
            interval_km=interval_km,
            interval_months=interval_months,
            next_change_date=next_change_date,
            source_repair_id=source_repair_id,
        )
        return self.repository.save(replacement, commit=commit)

    def _validate_repair_cost_conflict(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        replacement_date: date,
        component_price: int | None,
        work_price: int | None,
    ) -> None:
        """Запретить стоимость замены, если компонент входит в ремонт на эту дату."""
        has_price = (component_price or 0) > 0 or (work_price or 0) > 0
        if not has_price:
            return

        repair = self.repair_repository.find_repair_for_replacement(
            vehicle_id,
            component_type,
            replacement_date,
        )
        if repair:
            raise ValueError(
                _MSG_REPAIR_COST_CONFLICT.format(date=repair.repair_date)
            )

    def _validate_common(
        self,
        km: int,
        date_val: date,
    ) -> None:
        """Выполнить базовую валидацию пробега и даты."""
        if km < 0:
            raise ValueError(_MSG_NEGATIVE_KM)
        if date_val > date.today():
            raise ValueError(_MSG_FUTURE_DATE)

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
        if not last:
            return

        if exclude_id:
            prev, next_r = self.repository.find_neighbors(
                vehicle_id, component_type, km, exclude_id,
            )
            self._validate_previous(prev, km, date_val)
            self._validate_next(next_r, km, date_val)
            return

        self._validate_previous(last, km, date_val)

    @staticmethod
    def _validate_previous(
        previous: ReplacementDTO | None,
        km: int,
        date_val: date,
    ) -> None:
        """Проверить, что замена не раньше и не меньше предыдущей."""
        if not previous:
            return
        if km < previous.km_at_replacement:
            raise ValueError(
                _MSG_KM_LESS_THAN_PREVIOUS.format(
                    km=km,
                    previous_km=previous.km_at_replacement,
                )
            )
        if date_val < previous.replacement_date:
            raise ValueError(
                _MSG_DATE_LESS_THAN_PREVIOUS.format(
                    date=date_val,
                    previous_date=previous.replacement_date,
                )
            )

    @staticmethod
    def _validate_next(
        next_replacement: ReplacementDTO | None,
        km: int,
        date_val: date,
    ) -> None:
        """Проверить, что замена не позже и не больше следующей."""
        if not next_replacement:
            return
        if km > next_replacement.km_at_replacement:
            raise ValueError(
                _MSG_KM_GREATER_THAN_NEXT.format(
                    km=km,
                    next_km=next_replacement.km_at_replacement,
                )
            )
        if date_val > next_replacement.replacement_date:
            raise ValueError(
                _MSG_DATE_GREATER_THAN_NEXT.format(
                    date=date_val,
                    next_date=next_replacement.replacement_date,
                )
            )

    def _validate_no_duplicate(
        self,
        vehicle_id: int,
        component_type: ComponentType,
        km: int,
    ) -> None:
        """Проверить, что замена с таким пробегом для этого компонента ещё не существует."""
        existing = self.repository.find_by_vehicle_component_and_km(
            vehicle_id, component_type, km,
        )
        if existing:
            raise ValueError(_MSG_DUPLICATE_REPLACEMENT)

    def _update_vehicle_km_if_needed(
        self,
        vehicle_dto: VehicleDTO,
        new_km: int,
        commit: bool = True,
    ) -> None:
        """Обновить пробег автомобиля, если новый пробег больше текущего."""
        if new_km > vehicle_dto.current_km:
            vehicle_dto.current_km = new_km
            self.vehicle_repository.save(vehicle_dto, commit=commit)
