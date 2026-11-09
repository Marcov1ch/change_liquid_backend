from datetime import date, timedelta
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.replacement.schema import UpdateReplacementRequest
from app.api.tire_set.schema import (
    TireInstallRequest,
    TireSetCreateRequest,
    TireSetUpdateRequest,
)
from app.common.enums import ComponentType, TireEventType, TireSeason
from app.db.models import Base, BrandDB, ModelDB, VehicleDB
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import VehicleDTO
from app.services.replacement_service import ReplacementService
from app.services.tire_set_service import TireSetService

PAST_DATE = date.today() - timedelta(days=30)
PAST_DATE_2 = date.today() - timedelta(days=10)


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def vehicle(db_session: Session) -> VehicleDTO:
    db_session.add(BrandDB(id=1, name='VW'))
    db_session.add(ModelDB(id=1, brand_id=1, name='Golf'))
    db_session.add(VehicleDB(
        id=1,
        brand_id=1,
        model_id=1,
        plate_number='А123АА178',
        year=2015,
        current_km=10000,
        is_active=True,
        owner_id=1,
    ))
    db_session.commit()

    dto = VehicleRepository(db_session).find_active_by_id(1)
    assert dto is not None
    return dto


def _refresh_vehicle(db_session: Session) -> VehicleDTO:
    dto = VehicleRepository(db_session).find_active_by_id(1)
    assert dto is not None
    return dto


def _set_vehicle_km(db_session: Session, km: int) -> VehicleDTO:
    VehicleRepository(db_session).update_km(1, km)
    return _refresh_vehicle(db_session)


class TestTireSetCreate:

    def test_creates_purchase_record_in_purchase_month(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)

        tire_set = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние Michelin',
                season=TireSeason.WINTER,
                purchase_date=PAST_DATE,
                purchase_price=30000,
            ),
            vehicle,
        )

        assert tire_set.id is not None
        records = ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id)
        assert len(records) == 1
        purchase = records[0]
        assert purchase.tire_event_type == TireEventType.PURCHASE.value
        assert purchase.component_price == 30000
        assert purchase.work_price is None
        assert purchase.replacement_date == PAST_DATE

    def test_purchase_is_not_treated_as_latest_or_tire_mileage(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние Michelin',
                season=TireSeason.WINTER,
                purchase_price=30000,
            ),
            vehicle,
        )

        repository = ReplacementRepository(db_session)
        assert repository.get_latest_replacement_ids(1) == set()
        assert repository.get_last_replacement(1, ComponentType.TIRE_CHANGE) is None
        assert repository.get_last_replacement_with_notify(
            1, ComponentType.TIRE_CHANGE,
        ) is None
        assert repository.get_last_replacements_with_notify(1) == []
        assert service.replacement_service.get_tire_km_traveled(1, 10000) == {}
        assert tire_set.id is not None

    def test_no_purchase_record_without_price(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1,
            TireSetCreateRequest(name='Летние', season=TireSeason.SUMMER),
            vehicle,
        )

        assert tire_set.id is not None
        assert ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id) == []

    def test_create_with_install_now_creates_install_record_with_work_price(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)

        tire_set = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние',
                season=TireSeason.WINTER,
                purchase_price=30000,
                install_now=True,
                work_price=1500,
            ),
            vehicle,
        )

        assert tire_set.id is not None
        assert tire_set.is_installed is True

        records = ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id)
        purchase = next(
            item for item in records
            if item.tire_event_type == TireEventType.PURCHASE.value
        )
        install = next(
            item for item in records
            if item.tire_event_type == TireEventType.INSTALL.value
        )
        assert purchase.component_price == 30000
        assert install.work_price == 1500
        assert install.component_price is None

    def test_create_with_install_now_uses_purchase_date_as_install_date(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)

        tire_set = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние',
                season=TireSeason.WINTER,
                purchase_date=PAST_DATE,
                purchase_price=30000,
                install_now=True,
                work_price=1500,
            ),
            vehicle,
        )

        assert tire_set.id is not None
        assert tire_set.installed_date == PAST_DATE

        install = ReplacementRepository(db_session).get_last_install_for_tire_set(
            tire_set.id,
        )
        assert install is not None
        assert install.replacement_date == PAST_DATE
        assert install.work_price == 1500

    def test_create_with_install_now_stores_next_change_date(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        next_date = date.today() + timedelta(days=180)

        tire_set = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние',
                season=TireSeason.WINTER,
                install_now=True,
                next_change_date=next_date,
            ),
            vehicle,
        )

        assert tire_set.id is not None
        assert tire_set.next_change_date == next_date
        assert tire_set.status == 'good'
        assert tire_set.days_remaining == 180
        install = ReplacementRepository(db_session).get_last_install_for_tire_set(
            tire_set.id,
        )
        assert install is not None
        assert install.next_change_date == next_date

    def test_installed_set_status_warns_five_days_before(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        next_date = date.today() + timedelta(days=3)

        tire_set = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние',
                season=TireSeason.WINTER,
                install_now=True,
                next_change_date=next_date,
            ),
            vehicle,
        )

        assert tire_set.status == 'warning'
        assert tire_set.days_remaining == 3

    def test_not_installed_set_has_no_date_status(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )

        assert tire_set.status is None
        assert tire_set.days_remaining is None

    def test_purchase_without_date_uses_today_and_keeps_it_on_rename(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1,
            TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER, purchase_price=20000),
            vehicle,
        )
        assert tire_set.id is not None
        assert tire_set.purchase_date == date.today()

        service.update(tire_set.id, TireSetUpdateRequest(name='Зимние 2'), vehicle)

        records = ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id)
        assert len(records) == 1
        assert records[0].component_name == 'Зимние 2'
        assert records[0].replacement_date == date.today()

    def test_update_purchase_price_syncs_record(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние',
                season=TireSeason.WINTER,
                purchase_date=PAST_DATE_2,
                purchase_price=20000,
            ),
            vehicle,
        )
        assert tire_set.id is not None

        service.update(
            tire_set.id,
            TireSetUpdateRequest(
                purchase_date=PAST_DATE,
                purchase_price=25000,
            ),
            vehicle,
        )

        records = ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id)
        assert len(records) == 1
        assert records[0].component_price == 25000
        assert records[0].replacement_date == PAST_DATE

    def test_update_to_zero_price_removes_purchase_record(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1,
            TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER, purchase_price=20000),
            vehicle,
        )
        assert tire_set.id is not None

        service.update(tire_set.id, TireSetUpdateRequest(purchase_price=0), vehicle)

        assert ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id) == []


class TestPurchaseRecordProtection:

    def test_purchase_record_cannot_be_changed_via_replacement_service(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1,
            TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER, purchase_price=20000),
            vehicle,
        )
        assert tire_set.id is not None
        records = ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id)
        purchase_id = records[0].id
        assert purchase_id is not None

        replacement_service = ReplacementService(db_session)
        with pytest.raises(ValueError, match='через настройки комплекта'):
            replacement_service.update(
                purchase_id,
                UpdateReplacementRequest(component_price=1),
            )

        assert replacement_service.delete(purchase_id) is True
        assert ReplacementRepository(db_session).find_by_tire_set_id(tire_set.id) == []

        updated_set = service.get_by_id(tire_set.id)
        assert updated_set is not None
        assert updated_set.purchase_price is None
        assert updated_set.purchase_date is None


class TestTireHistoryDeletion:

    def test_delete_install_event_keeps_set_state(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        assert tire_set.id is not None
        _, install = service.install(
            1, tire_set.id, TireInstallRequest(), vehicle,
        )
        assert install.id is not None

        assert ReplacementService(db_session).delete(install.id) is True

        updated = service.get_by_id(tire_set.id, vehicle.current_km)
        assert updated is not None
        assert updated.is_installed is True
        assert service.replacement_service.get_tire_km_traveled(1, vehicle.current_km) == {}


class TestTireSetInstall:

    def test_switch_accumulates_mileage_per_set(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        winter = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        summer = service.create(
            1, TireSetCreateRequest(name='Летние', season=TireSeason.SUMMER), vehicle,
        )
        assert winter.id is not None and summer.id is not None

        service.install(1, winter.id, TireInstallRequest(switch_date=date.today()), vehicle)
        vehicle = _set_vehicle_km(db_session, 20000)
        service.install(1, summer.id, TireInstallRequest(switch_date=date.today()), vehicle)
        vehicle = _set_vehicle_km(db_session, 40000)
        service.install(1, winter.id, TireInstallRequest(switch_date=date.today()), vehicle)
        vehicle = _set_vehicle_km(db_session, 45000)

        winter_after = service.get_by_id(winter.id, vehicle.current_km)
        summer_after = service.get_by_id(summer.id, vehicle.current_km)
        assert winter_after is not None and summer_after is not None
        assert winter_after.is_installed is True
        assert winter_after.total_km == 15000
        assert summer_after.is_installed is False
        assert summer_after.total_km == 20000

    def test_install_creates_zero_cost_replacement(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        assert tire_set.id is not None

        _, replacement = service.install(
            1, tire_set.id, TireInstallRequest(switch_date=date.today()), vehicle,
        )

        assert replacement.tire_set_id == tire_set.id
        assert replacement.tire_event_type == TireEventType.INSTALL.value
        assert replacement.component_price is None
        assert replacement.work_price is None
        assert replacement.km_at_replacement == vehicle.current_km

    def test_install_stores_optional_work_price(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        assert tire_set.id is not None

        _, replacement = service.install(
            1,
            tire_set.id,
            TireInstallRequest(switch_date=date.today(), work_price=1500),
            vehicle,
        )

        assert replacement.work_price == 1500

    def test_update_next_change_date_for_installed_set(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        assert tire_set.id is not None
        service.install(1, tire_set.id, TireInstallRequest(), vehicle)

        repository = ReplacementRepository(db_session)
        install = repository.get_last_install_for_tire_set(tire_set.id)
        assert install is not None and install.id is not None
        repository.update_date_notify_tracking(
            install.id,
            date_warning_notified=True,
            date_overdue_notified=True,
        )

        next_date = date.today() + timedelta(days=150)
        updated = service.update(
            tire_set.id,
            TireSetUpdateRequest(next_change_date=next_date),
            vehicle,
        )

        assert updated.next_change_date == next_date
        assert updated.status == 'good'
        assert updated.days_remaining == 150
        install_after = repository.get_last_install_for_tire_set(tire_set.id)
        assert install_after is not None
        assert install_after.next_change_date == next_date

        last_with_notify = repository.get_last_replacement_with_notify(
            1, ComponentType.TIRE_CHANGE,
        )
        assert last_with_notify is not None
        assert last_with_notify["date_warning_notified"] is False
        assert last_with_notify["date_overdue_notified"] is False

    def test_update_next_change_date_requires_installed_set(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        assert tire_set.id is not None

        with pytest.raises(ValueError, match='только для установленного'):
            service.update(
                tire_set.id,
                TireSetUpdateRequest(next_change_date=date.today()),
                vehicle,
            )

    def test_cannot_install_already_installed_set(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        assert tire_set.id is not None
        service.install(1, tire_set.id, TireInstallRequest(), vehicle)

        with pytest.raises(ValueError, match='уже установлен'):
            service.install(1, tire_set.id, TireInstallRequest(), vehicle)

    def test_only_one_set_stays_installed(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        winter = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        summer = service.create(
            1, TireSetCreateRequest(name='Летние', season=TireSeason.SUMMER), vehicle,
        )
        assert winter.id is not None and summer.id is not None

        service.install(1, winter.id, TireInstallRequest(), vehicle)
        service.install(1, summer.id, TireInstallRequest(), vehicle)

        sets = service.get_by_vehicle(1, vehicle.current_km)
        installed = [item for item in sets if item.is_installed]
        assert len(installed) == 1
        assert installed[0].id == summer.id

    def test_delete_installed_set_is_forbidden(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        tire_set = service.create(
            1, TireSetCreateRequest(name='Зимние', season=TireSeason.WINTER), vehicle,
        )
        assert tire_set.id is not None
        service.install(1, tire_set.id, TireInstallRequest(), vehicle)

        with pytest.raises(ValueError, match='установленный'):
            service.delete(tire_set.id)

    def test_delete_keeps_purchase_and_install_history(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = TireSetService(db_session)
        winter = service.create(
            1,
            TireSetCreateRequest(
                name='Зимние',
                season=TireSeason.WINTER,
                purchase_price=30000,
            ),
            vehicle,
        )
        summer = service.create(
            1, TireSetCreateRequest(name='Летние', season=TireSeason.SUMMER), vehicle,
        )
        assert winter.id is not None and summer.id is not None

        service.install(1, winter.id, TireInstallRequest(), vehicle)
        service.install(1, summer.id, TireInstallRequest(), vehicle)
        service.delete(winter.id)

        assert service.get_by_id(winter.id, vehicle.current_km) is None

        winter_records = ReplacementRepository(db_session).find_by_tire_set_id(winter.id)
        assert winter_records == []

        all_records = ReplacementRepository(db_session).find_by_vehicle_id(1)
        detached = [
            item for item in all_records
            if item.tire_set_id is None
            and item.tire_event_type in (
                TireEventType.PURCHASE.value,
                TireEventType.INSTALL.value,
            )
        ]
        assert any(
            item.tire_event_type == TireEventType.PURCHASE.value
            for item in detached
        )
        assert any(
            item.tire_event_type == TireEventType.INSTALL.value
            for item in detached
        )

        sets = service.get_by_vehicle(1, vehicle.current_km)
        assert all(item.id != winter.id for item in sets)
