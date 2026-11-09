from datetime import date

from sqlalchemy.orm import Session

from app.api.replacement.schema import ReplacementCreateRequest
from app.api.tire_set.schema import (
    TireInstallRequest,
    TireSetCreateRequest,
    TireSetUpdateRequest,
)
from app.common.constants import get_date_warning_days
from app.common.enums import ComponentType, TireEventType
from app.common.utils.calculator import StatusCalculator
from app.repository.replacement_repository import ReplacementRepository
from app.repository.tire_set_repository import TireSetRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import ReplacementDTO, TireSetDTO, VehicleDTO
from app.services.replacement_service import ReplacementService

_MSG_VEHICLE_NOT_FOUND = 'Автомобиль с ID {vehicle_id} не найден'
_MSG_SET_NOT_FOUND = 'Комплект шин с ID {set_id} не найден'
_MSG_SET_ALREADY_INSTALLED = 'Этот комплект шин уже установлен'
_MSG_INSTALLED_SET_DELETE = 'Нельзя удалить установленный комплект шин'
_MSG_FUTURE_PURCHASE_DATE = 'Дата покупки не может быть позже сегодняшнего дня'
_MSG_FUTURE_SWITCH_DATE = 'Дата переключения не может быть позже сегодняшнего дня'
_MSG_NEXT_DATE_BEFORE_SWITCH = 'Дата следующей смены не может быть раньше даты переключения'
_MSG_NEXT_DATE_ONLY_INSTALLED = 'Дату следующей смены можно задать только для установленного комплекта'
_MSG_INSTALL_EVENT_NOT_FOUND = 'Запись установки комплекта не найдена'
_MSG_NEXT_DATE_BEFORE_INSTALL = 'Дата следующей смены не может быть раньше даты установки'
_MSG_NEGATIVE_PURCHASE_PRICE = 'Стоимость покупки не может быть отрицательной'


class TireSetService:
    """Класс для работы с комплектами шин."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = TireSetRepository(db)
        self.replacement_repository = ReplacementRepository(db)
        self.vehicle_repository = VehicleRepository(db)
        self.replacement_service = ReplacementService(db)

    def get_by_id(
        self,
        tire_set_id: int,
        current_km: int | None = None,
    ) -> TireSetDTO | None:
        """Получить комплект шин по id."""
        tire_set = self.repository.find_by_id(tire_set_id, current_km)
        if tire_set is not None:
            self._enrich_next_change_date(tire_set)
        return tire_set

    def get_by_vehicle(
        self,
        vehicle_id: int,
        current_km: int | None = None,
    ) -> list[TireSetDTO]:
        """Получить все комплекты шин автомобиля."""
        tire_sets = self.repository.find_by_vehicle(vehicle_id, current_km)
        for tire_set in tire_sets:
            self._enrich_next_change_date(tire_set)
        return tire_sets  # type: ignore[no-any-return]

    def create(
        self,
        vehicle_id: int,
        request: TireSetCreateRequest,
        vehicle_dto: VehicleDTO | None = None,
        commit: bool = True,
    ) -> TireSetDTO:
        """Создать комплект шин и запись о его покупке."""
        if vehicle_dto is None:
            vehicle_dto = self.vehicle_repository.find_active_by_id(vehicle_id)
        if not vehicle_dto:
            raise ValueError(_MSG_VEHICLE_NOT_FOUND.format(vehicle_id=vehicle_id))

        purchase_date = self._resolve_purchase_date(
            request.purchase_date,
            request.purchase_price,
        )
        self._validate_purchase(purchase_date, request.purchase_price)

        tire_set = TireSetDTO(
            id=None,
            vehicle_id=vehicle_id,
            name=request.name,
            season=request.season.value,
            purchase_date=purchase_date,
            purchase_price=request.purchase_price,
            accumulated_km=0,
            is_installed=False,
        )
        saved = self.repository.save(tire_set, vehicle_dto.current_km, commit=False)
        self._sync_purchase_record(saved, vehicle_dto, commit=False)
        if request.install_now and saved.id is not None:
            self.install(
                vehicle_id,
                saved.id,
                TireInstallRequest(
                    work_price=request.work_price,
                    next_change_date=request.next_change_date,
                ),
                vehicle_dto,
                commit=False,
            )
        self._finalize(commit)
        return self._load(saved.id or 0, vehicle_dto.current_km) or saved

    def update(
        self,
        tire_set_id: int,
        request: TireSetUpdateRequest,
        vehicle_dto: VehicleDTO | None = None,
        commit: bool = True,
    ) -> TireSetDTO:
        """Обновить комплект шин и синхронизировать запись о покупке."""
        tire_set = self.repository.find_by_id(tire_set_id)
        if not tire_set:
            raise ValueError(_MSG_SET_NOT_FOUND.format(set_id=tire_set_id))

        if vehicle_dto is None:
            vehicle_dto = self.vehicle_repository.find_active_by_id(tire_set.vehicle_id)
        if not vehicle_dto:
            raise ValueError(
                _MSG_VEHICLE_NOT_FOUND.format(vehicle_id=tire_set.vehicle_id)
            )

        if request.name is not None:
            tire_set.name = request.name
        if request.season is not None:
            tire_set.season = request.season.value
        if request.purchase_date is not None:
            tire_set.purchase_date = request.purchase_date
        if request.purchase_price is not None:
            tire_set.purchase_price = request.purchase_price

        tire_set.purchase_date = self._resolve_purchase_date(
            tire_set.purchase_date,
            tire_set.purchase_price,
        )
        self._validate_purchase(tire_set.purchase_date, tire_set.purchase_price)

        saved = self.repository.save(tire_set, vehicle_dto.current_km, commit=False)
        self._sync_purchase_record(saved, vehicle_dto, commit=False)

        if 'next_change_date' in request.model_fields_set:
            self._update_next_change_date(
                saved,
                request.next_change_date,
                commit=False,
            )

        self._finalize(commit)
        return self._load(saved.id or 0, vehicle_dto.current_km) or saved

    def delete(self, tire_set_id: int, commit: bool = True) -> bool:
        """Удалить комплект, сохранив его историю покупки и установок."""
        tire_set = self.repository.find_by_id(tire_set_id)
        if not tire_set:
            return False
        if tire_set.is_installed:
            raise ValueError(_MSG_INSTALLED_SET_DELETE)

        self.replacement_repository.clear_tire_set_id(tire_set_id, commit=False)
        deleted = self.repository.delete(tire_set_id, commit=False)
        self._finalize(commit)
        return bool(deleted)

    def install(
        self,
        vehicle_id: int,
        tire_set_id: int,
        request: TireInstallRequest,
        vehicle_dto: VehicleDTO | None = None,
        commit: bool = True,
    ) -> tuple[TireSetDTO, ReplacementDTO]:
        """Переключить автомобиль на указанный комплект шин."""
        if vehicle_dto is None:
            vehicle_dto = self.vehicle_repository.find_active_by_id(vehicle_id)
        if not vehicle_dto:
            raise ValueError(_MSG_VEHICLE_NOT_FOUND.format(vehicle_id=vehicle_id))

        target = self.repository.find_by_id(tire_set_id, vehicle_dto.current_km)
        if not target or target.vehicle_id != vehicle_id:
            raise ValueError(_MSG_SET_NOT_FOUND.format(set_id=tire_set_id))
        if target.is_installed:
            raise ValueError(_MSG_SET_ALREADY_INSTALLED)

        switch_date = request.switch_date or date.today()
        next_change_date = request.next_change_date
        if switch_date > date.today():
            raise ValueError(_MSG_FUTURE_SWITCH_DATE)
        if next_change_date is not None and next_change_date < switch_date:
            raise ValueError(_MSG_NEXT_DATE_BEFORE_SWITCH)

        self._close_installed_set(vehicle_id, vehicle_dto, commit=False)

        target.installed_km = vehicle_dto.current_km
        target.installed_date = switch_date
        target.is_installed = True
        saved_target = self.repository.save(
            target,
            vehicle_dto.current_km,
            commit=False,
        )

        replacement = self.replacement_service.create(
            vehicle_id,
            ReplacementCreateRequest(
                component_type=ComponentType.TIRE_CHANGE,
                component_name=saved_target.name,
                component_price=None,
                work_price=request.work_price,
                replacement_date=switch_date,
                km_at_replacement=vehicle_dto.current_km,
                next_change_date=next_change_date,
            ),
            vehicle_dto,
            commit=False,
            tire_set_id=tire_set_id,
            tire_event_type=TireEventType.INSTALL.value,
        )

        self._finalize(commit)
        updated = self._load(tire_set_id, vehicle_dto.current_km) or saved_target
        return updated, replacement

    def delete_by_vehicle(self, vehicle_id: int, commit: bool = True) -> int:
        """Удалить все комплекты шин автомобиля."""
        return self.repository.delete_by_vehicle(vehicle_id, commit)  # type: ignore[no-any-return]

    def _load(self, tire_set_id: int, current_km: int | None) -> TireSetDTO | None:
        """Загрузить комплект и заполнить дату следующей смены."""
        tire_set = self.repository.find_by_id(tire_set_id, current_km)
        if tire_set is not None:
            self._enrich_next_change_date(tire_set)
        return tire_set

    def _enrich_next_change_date(self, tire_set: TireSetDTO) -> None:
        """Подставить дату следующей смены и статус из последней установки."""
        if tire_set.id is None:
            tire_set.next_change_date = None
            tire_set.status = None
            tire_set.days_remaining = None
            return

        install = self.replacement_repository.get_last_install_for_tire_set(tire_set.id)
        tire_set.next_change_date = install.next_change_date if install else None
        if not tire_set.is_installed:
            tire_set.status = None
            tire_set.days_remaining = None
            return

        status_data = StatusCalculator.calculate_date_status(
            tire_set.next_change_date,
            get_date_warning_days(ComponentType.TIRE_CHANGE),
        )
        tire_set.status = status_data["status"]
        tire_set.days_remaining = status_data["days_remaining"]

    def _update_next_change_date(
        self,
        tire_set: TireSetDTO,
        next_change_date: date | None,
        commit: bool,
    ) -> None:
        """Обновить дату следующей смены у установленного комплекта."""
        if not tire_set.is_installed:
            raise ValueError(_MSG_NEXT_DATE_ONLY_INSTALLED)
        if tire_set.id is None:
            raise ValueError(_MSG_SET_NOT_FOUND.format(set_id='?'))

        install = self.replacement_repository.get_last_install_for_tire_set(tire_set.id)
        if install is None or install.id is None:
            raise ValueError(_MSG_INSTALL_EVENT_NOT_FOUND)
        if (
            next_change_date is not None
            and tire_set.installed_date is not None
            and next_change_date < tire_set.installed_date
        ):
            raise ValueError(_MSG_NEXT_DATE_BEFORE_INSTALL)

        install_id = install.id
        install.next_change_date = next_change_date
        self.replacement_repository.save(install, commit=commit)
        self.replacement_repository.update_date_notify_tracking(
            install_id,
            date_warning_notified=False,
            date_overdue_notified=False,
            commit=commit,
        )

    def _close_installed_set(
        self,
        vehicle_id: int,
        vehicle_dto: VehicleDTO,
        commit: bool,
    ) -> None:
        """Закрыть текущий установленный комплект и накопить его пробег."""
        current = self.repository.find_installed(vehicle_id)
        if not current or current.id is None:
            return

        if current.installed_km is not None:
            current.accumulated_km += max(
                0,
                vehicle_dto.current_km - current.installed_km,
            )
        current.installed_km = None
        current.installed_date = None
        current.is_installed = False
        self.repository.save(current, vehicle_dto.current_km, commit=commit)

    def _sync_purchase_record(
        self,
        tire_set: TireSetDTO,
        vehicle_dto: VehicleDTO,
        commit: bool,
    ) -> None:
        """Создать, обновить или удалить запись о покупке комплекта."""
        if tire_set.id is None:
            return

        existing = self.replacement_repository.find_tire_event(
            tire_set.vehicle_id,
            tire_set.id,
            TireEventType.PURCHASE,
        )
        has_price = (tire_set.purchase_price or 0) > 0

        if not has_price:
            if existing and existing.id is not None:
                self.replacement_repository.delete(existing.id, commit=commit)
            return

        purchase_date = tire_set.purchase_date or date.today()
        if existing is None:
            self.replacement_service.create(
                tire_set.vehicle_id,
                ReplacementCreateRequest(
                    component_type=ComponentType.TIRE_CHANGE,
                    component_name=tire_set.name,
                    component_price=tire_set.purchase_price,
                    work_price=None,
                    replacement_date=purchase_date,
                    km_at_replacement=vehicle_dto.current_km,
                    next_change_date=None,
                ),
                vehicle_dto,
                commit=commit,
                tire_set_id=tire_set.id,
                tire_event_type=TireEventType.PURCHASE.value,
            )
            return

        existing.component_name = tire_set.name
        existing.component_price = tire_set.purchase_price
        existing.replacement_date = purchase_date
        existing.tire_event_type = TireEventType.PURCHASE.value
        self.replacement_repository.save(existing, commit=commit)

    @staticmethod
    def _resolve_purchase_date(
        purchase_date: date | None,
        purchase_price: int | None,
    ) -> date | None:
        """Подставить сегодняшнюю дату, если покупка платная и дата не указана."""
        if purchase_date is None and (purchase_price or 0) > 0:
            return date.today()
        return purchase_date

    @staticmethod
    def _validate_purchase(
        purchase_date: date | None,
        purchase_price: int | None,
    ) -> None:
        """Проверить дату и стоимость покупки комплекта."""
        if purchase_date is not None and purchase_date > date.today():
            raise ValueError(_MSG_FUTURE_PURCHASE_DATE)
        if purchase_price is not None and purchase_price < 0:
            raise ValueError(_MSG_NEGATIVE_PURCHASE_PRICE)

    def _finalize(self, commit: bool) -> None:
        """Зафиксировать или сбросить изменения в БД."""
        if commit:
            self.db.commit()
        else:
            self.db.flush()
