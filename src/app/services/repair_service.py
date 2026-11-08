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

        self._validate_date(request.repair_date)
        self._validate_km(request.km_at_repair)
        self._validate_costs(request.work_cost, request.parts_cost)
        component_types = self._normalize_components(request.component_types)

        old_date = repair.repair_date
        old_km = repair.km_at_repair
        old_types = set(repair.component_types)
        new_types = set(component_types)

        linked = self.replacement_repository.find_by_source_repair_id(repair_id)

        conflicts = self.repository.find_priced_component_types(
            repair.vehicle_id,
            request.repair_date,
            component_types,
        )
        if conflicts:
            raise self._conflict_error(sorted(conflicts)[0], request.repair_date)

        saved = self.repository.save(
            RepairDTO(
                id=repair.id,
                vehicle_id=repair.vehicle_id,
                repair_date=request.repair_date,
                km_at_repair=request.km_at_repair,
                description=self._normalize_description(request.description),
                work_cost=request.work_cost,
                parts_cost=request.parts_cost,
                component_types=component_types,
            ),
            commit=False,
        )
        self._update_vehicle_km(vehicle_dto, request.km_at_repair)

        removed_types = old_types - new_types
        moved_untouched: set[ComponentType] = set()

        for replacement in linked:
            component_type = replacement.component_type
            untouched = self._is_untouched_placeholder(replacement, old_date, old_km)

            if component_type in removed_types:
                if untouched:
                    self.replacement_repository.delete(
                        replacement.id, commit=False,  # type: ignore[arg-type]
                    )
                else:
                    replacement.source_repair_id = None
                    self.replacement_repository.save(replacement, commit=False)
                continue

            if (
                untouched
                and (old_date != request.repair_date or old_km != request.km_at_repair)
            ):
                self.replacement_repository.delete(
                    replacement.id, commit=False,  # type: ignore[arg-type]
                )
                moved_untouched.add(component_type)

        for component_type in component_types:
            if component_type in (new_types - old_types) or component_type in moved_untouched:
                self._ensure_placeholder(
                    vehicle_dto,
                    repair.id,
                    component_type,
                    request.repair_date,
                    request.km_at_repair,
                )

        if commit:
            self.db.commit()

        return self.repository.find_by_id(repair_id) or saved

    def delete(self, repair_id: int, commit: bool = True) -> bool:
        """Удалить ремонт, удалив нетронутые и отвязав изменённые замены."""
        repair = self.repository.find_by_id(repair_id)
        if not repair:
            return False

        linked = self.replacement_repository.find_by_source_repair_id(repair_id)
        for replacement in linked:
            if self._is_untouched_placeholder(
                replacement,
                repair.repair_date,
                repair.km_at_repair,
            ):
                self.replacement_repository.delete(
                    replacement.id, commit=False,  # type: ignore[arg-type]
                )
            else:
                replacement.source_repair_id = None
                self.replacement_repository.save(replacement, commit=False)

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
