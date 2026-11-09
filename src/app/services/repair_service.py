from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.api.repair.schema import RepairCreateRequest
from app.common.component_config import COMPONENTS_CONFIG
from app.common.enums import ComponentType
from app.repository.repair_repository import RepairRepository
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import RepairDTO, ReplacementDTO, VehicleDTO
from app.services.replacement_service import REPAIR_PLACEHOLDER_NAME, ReplacementService

_MSG_VEHICLE_NOT_FOUND = 'Автомобиль не найден'
_MSG_FUTURE_DATE = 'Дата ремонта не может быть позже сегодняшнего дня'
_MSG_NEGATIVE_KM = 'Пробег ремонта не может быть отрицательным'
_MSG_NEGATIVE_COST = 'Стоимость работ и запчастей не может быть отрицательной'
_MSG_INVALID_COMPONENT = 'Компонент `{name}` нельзя добавить в ремонт'
_MSG_PRICED_REPLACEMENT = 'На {date} уже есть замена с ценой для компонента `{name}`'

_ALLOWED_COMPONENT_TYPES = {config.type for config in COMPONENTS_CONFIG}
_COMPONENT_NAMES = {config.type: config.name for config in COMPONENTS_CONFIG}


@dataclass
class _RepairUpdate:
    """Итоговые значения ремонта после частичного обновления."""
    repair: RepairDTO
    vehicle_dto: VehicleDTO
    description: str | None
    repair_date: date
    km_at_repair: int
    work_cost: int
    parts_cost: int
    component_types: list[ComponentType]
    old_date: date
    old_km: int
    old_types: set[ComponentType]
    new_types: set[ComponentType]
    linked: list[ReplacementDTO]


class RepairService:
    """Класс для работы с ремонтами."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = RepairRepository(db)
        self.replacement_repository = ReplacementRepository(db)
        self.replacement_service = ReplacementService(db)
        self.vehicle_repository = VehicleRepository(db)

    @staticmethod
    def _validate_date(repair_date: date) -> None:
        if repair_date > date.today():
            raise ValueError(_MSG_FUTURE_DATE)

    @staticmethod
    def _validate_km(km_at_repair: int) -> None:
        if km_at_repair < 0:
            raise ValueError(_MSG_NEGATIVE_KM)

    @staticmethod
    def _validate_costs(work_cost: int, parts_cost: int) -> None:
        if work_cost < 0 or parts_cost < 0:
            raise ValueError(_MSG_NEGATIVE_COST)

    @staticmethod
    def _normalize_description(description: str | None) -> str | None:
        if description is None:
            return None
        normalized = description.strip()
        return normalized or None

    @staticmethod
    def _normalize_components(component_types: list[ComponentType]) -> list[ComponentType]:
        normalized: list[ComponentType] = []
        seen: set[ComponentType] = set()

        for component_type in component_types:
            if component_type not in _ALLOWED_COMPONENT_TYPES:
                name = component_type.value
                raise ValueError(_MSG_INVALID_COMPONENT.format(name=name))
            if component_type in seen:
                continue
            seen.add(component_type)
            normalized.append(component_type)

        return normalized

    @staticmethod
    def _conflict_error(component_type: str, repair_date: date) -> ValueError:
        name = _COMPONENT_NAMES.get(ComponentType(component_type), component_type)
        return ValueError(
            _MSG_PRICED_REPLACEMENT.format(date=repair_date, name=name)
        )

    @staticmethod
    def _is_untouched_placeholder(
        replacement: ReplacementDTO,
        repair_date: date,
        km_at_repair: int,
    ) -> bool:
        return (
            replacement.component_name == REPAIR_PLACEHOLDER_NAME
            and not (replacement.component_price or 0)
            and not (replacement.work_price or 0)
            and replacement.replacement_date == repair_date
            and replacement.km_at_replacement == km_at_repair
        )

    def create(
        self,
        vehicle_id: int,
        request: RepairCreateRequest,
        vehicle_dto: VehicleDTO | None = None,
        commit: bool = True,
    ) -> RepairDTO:
        """Создать ремонт и служебные замены для выбранных компонентов."""
        if vehicle_dto is None:
            vehicle_dto = self.vehicle_repository.find_active_by_id(vehicle_id)
        if not vehicle_dto:
            raise ValueError(_MSG_VEHICLE_NOT_FOUND)

        self._validate_date(request.repair_date)
        self._validate_km(request.km_at_repair)
        self._validate_costs(request.work_cost, request.parts_cost)
        component_types = self._normalize_components(request.component_types)

        conflicts = self.repository.find_priced_component_types(
            vehicle_id,
            request.repair_date,
            component_types,
        )
        if conflicts:
            raise self._conflict_error(sorted(conflicts)[0], request.repair_date)

        repair = RepairDTO(
            id=None,
            vehicle_id=vehicle_id,
            repair_date=request.repair_date,
            km_at_repair=request.km_at_repair,
            description=self._normalize_description(request.description),
            work_cost=request.work_cost,
            parts_cost=request.parts_cost,
            component_types=component_types,
        )

        saved = self.repository.save(repair, commit=False)
        self._update_vehicle_km(vehicle_dto, request.km_at_repair)

        for component_type in component_types:
            self._ensure_placeholder(
                vehicle_dto,
                saved.id,
                component_type,
                request.repair_date,
                request.km_at_repair,
            )

        if commit:
            self.db.commit()

        return self.repository.find_by_id(saved.id) if saved.id else saved  # type: ignore[return-value]

    def get_by_id(self, repair_id: int) -> RepairDTO | None:
        """Получить ремонт по id."""
        return self.repository.find_by_id(repair_id)

    def get_by_vehicle(self, vehicle_id: int) -> list[RepairDTO]:
        """Получить ремонты автомобиля."""
        return self.repository.find_by_vehicle_id(vehicle_id)  # type: ignore[no-any-return]

    def update(
        self,
        repair_id: int,
        request: RepairCreateRequest,
        commit: bool = True,
    ) -> RepairDTO | None:
        """Полностью обновить ремонт и синхронизировать служебные замены."""
        repair = self.repository.find_by_id(repair_id)
        if not repair:
            return None

        vehicle_dto = self.vehicle_repository.find_active_by_id(repair.vehicle_id)
        if not vehicle_dto:
            raise ValueError(_MSG_VEHICLE_NOT_FOUND)

        update = self._resolve_update(repair, request, vehicle_dto)
        self._validate_update(update)
        return self._apply_update(update, commit)

    def _resolve_update(
        self,
        repair: RepairDTO,
        request: RepairCreateRequest,
        vehicle_dto: VehicleDTO,
    ) -> _RepairUpdate:
        """Собрать итоговые значения ремонта из запроса."""
        self._validate_date(request.repair_date)
        self._validate_km(request.km_at_repair)
        self._validate_costs(request.work_cost, request.parts_cost)
        component_types = self._normalize_components(request.component_types)

        return _RepairUpdate(
            repair=repair,
            vehicle_dto=vehicle_dto,
            description=self._normalize_description(request.description),
            repair_date=request.repair_date,
            km_at_repair=request.km_at_repair,
            work_cost=request.work_cost,
            parts_cost=request.parts_cost,
            component_types=component_types,
            old_date=repair.repair_date,
            old_km=repair.km_at_repair,
            old_types=set(repair.component_types),
            new_types=set(component_types),
            linked=self.replacement_repository.find_by_source_repair_id(repair.id or 0),
        )

    def _validate_update(self, update: _RepairUpdate) -> None:
        """Проверить конфликты обновлённого ремонта с платными заменами."""
        conflicts = self.repository.find_priced_component_types(
            update.repair.vehicle_id,
            update.repair_date,
            update.component_types,
        )
        if conflicts:
            raise self._conflict_error(sorted(conflicts)[0], update.repair_date)

    def _apply_update(self, update: _RepairUpdate, commit: bool) -> RepairDTO:
        """Записать ремонт и синхронизировать служебные замены."""
        saved = self.repository.save(
            RepairDTO(
                id=update.repair.id,
                vehicle_id=update.repair.vehicle_id,
                repair_date=update.repair_date,
                km_at_repair=update.km_at_repair,
                description=update.description,
                work_cost=update.work_cost,
                parts_cost=update.parts_cost,
                component_types=update.component_types,
            ),
            commit=False,
        )
        self._update_vehicle_km(update.vehicle_dto, update.km_at_repair)
        moved_untouched = self._sync_existing_placeholders(update)
        self._create_missing_placeholders(update, moved_untouched)

        if commit:
            self.db.commit()

        return self.repository.find_by_id(update.repair.id or 0) or saved

    def _sync_existing_placeholders(
        self,
        update: _RepairUpdate,
    ) -> set[ComponentType]:
        """Удалить/отвязать лишние placeholders и вернуть перемещённые."""
        removed_types = update.old_types - update.new_types
        location_changed = (
            update.old_date != update.repair_date
            or update.old_km != update.km_at_repair
        )
        moved_untouched: set[ComponentType] = set()

        for replacement in update.linked:
            untouched = self._is_untouched_placeholder(
                replacement,
                update.old_date,
                update.old_km,
            )
            if replacement.component_type in removed_types:
                self._remove_or_detach_placeholder(replacement, untouched)
                continue

            if untouched and location_changed:
                self._delete_placeholder(replacement)
                moved_untouched.add(replacement.component_type)

        return moved_untouched

    def _create_missing_placeholders(
        self,
        update: _RepairUpdate,
        moved_untouched: set[ComponentType],
    ) -> None:
        """Создать placeholders для новых и перемещённых компонентов."""
        added_types = update.new_types - update.old_types
        for component_type in update.component_types:
            if component_type in added_types or component_type in moved_untouched:
                self._ensure_placeholder(
                    update.vehicle_dto,
                    update.repair.id or 0,
                    component_type,
                    update.repair_date,
                    update.km_at_repair,
                )

    def _remove_or_detach_placeholder(
        self,
        replacement: ReplacementDTO,
        untouched: bool,
    ) -> None:
        """Удалить нетронутый placeholder или отвязать изменённый."""
        if untouched:
            self._delete_placeholder(replacement)
            return

        replacement.source_repair_id = None
        self.replacement_repository.save(replacement, commit=False)

    def _delete_placeholder(self, replacement: ReplacementDTO) -> None:
        """Удалить placeholder, если у него есть id."""
        if replacement.id is not None:
            self.replacement_repository.delete(replacement.id, commit=False)

    def delete(self, repair_id: int, commit: bool = True) -> bool:
        """Удалить ремонт, удалив нетронутые и отвязав изменённые замены."""
        repair = self.repository.find_by_id(repair_id)
        if not repair:
            return False

        linked = self.replacement_repository.find_by_source_repair_id(repair_id)
        for replacement in linked:
            untouched = self._is_untouched_placeholder(
                replacement,
                repair.repair_date,
                repair.km_at_repair,
            )
            self._remove_or_detach_placeholder(replacement, untouched)

        self.repository.delete(repair_id, commit=commit)
        return True

    def delete_by_vehicle(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все ремонты автомобиля."""
        return self.repository.delete_by_vehicle_id(vehicle_id, commit)  # type: ignore[no-any-return]

    def _ensure_placeholder(
        self,
        vehicle_dto: VehicleDTO,
        repair_id: int,
        component_type: ComponentType,
        repair_date: date,
        km_at_repair: int,
    ) -> None:
        existing = self.replacement_repository.find_by_vehicle_component_and_date(
            vehicle_dto.id,  # type: ignore[arg-type]
            component_type,
            repair_date,
        )
        if existing:
            return

        self.replacement_service.create_repair_placeholder(
            vehicle_dto,
            component_type,
            repair_date,
            km_at_repair,
            repair_id,
            commit=False,
        )

    def _update_vehicle_km(self, vehicle_dto: VehicleDTO, km_at_repair: int) -> None:
        if km_at_repair > vehicle_dto.current_km:
            vehicle_dto.current_km = km_at_repair
            self.vehicle_repository.save(vehicle_dto, commit=False)
