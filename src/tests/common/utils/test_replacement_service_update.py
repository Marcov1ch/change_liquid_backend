from datetime import date
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.repair.schema import RepairCreateRequest
from app.api.replacement.schema import UpdateReplacementRequest
from app.common.enums import ComponentType
from app.db.models import Base, BrandDB, ModelDB, ReplacementDB, VehicleDB
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import ReplacementDTO, VehicleDTO
from app.services.repair_service import RepairService
from app.services.replacement_service import ReplacementService


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
        plate_number='AB-123-CD',
        year=2015,
        current_km=10000,
        is_active=True,
        owner_id=1,
    ))
    db_session.commit()

    dto = VehicleRepository(db_session).find_active_by_id(1)
    assert dto is not None
    return dto


def _service(db_session: Session) -> ReplacementService:
    return ReplacementService(db_session)


def _update(
    service: ReplacementService,
    replacement_id: int,
    **fields: object,
) -> ReplacementDTO | None:
    return service.update(
        replacement_id,
        UpdateReplacementRequest.model_construct(**fields),
    )


def _add_replacement(
    db_session: Session,
    component_type: ComponentType = ComponentType.ENGINE_OIL,
    replacement_date: date = date(2026, 1, 15),
    km: int = 12000,
    next_change_date: date | None = date(2027, 1, 15),
    component_price: int = 5000,
    work_price: int = 1000,
    interval_km: int = 7000,
    interval_months: int | None = 12,
) -> ReplacementDTO:
    return ReplacementRepository(db_session).save(ReplacementDTO(
        id=None,
        vehicle_id=1,
        component_type=component_type,
        component_name='Тестовая замена',
        component_price=component_price,
        work_price=work_price,
        replacement_date=replacement_date,
        km_at_replacement=km,
        interval_km=interval_km,
        interval_months=interval_months,
        next_change_date=next_change_date,
    ))


def _set_date_flags(db_session: Session, replacement_id: int) -> None:
    ReplacementRepository(db_session).update_date_notify_tracking(
        replacement_id,
        date_warning_notified=True,
        date_overdue_notified=True,
    )


def _date_flags(db_session: Session, replacement_id: int) -> tuple[bool, bool]:
    row = db_session.query(ReplacementDB).filter(
        ReplacementDB.id == replacement_id
    ).one()
    return bool(row.date_warning_notified), bool(row.date_overdue_notified)


def test_update_name_only_keeps_other_fields(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(db_session)
    service = _service(db_session)

    updated = _update(service, replacement.id, component_name='Новое масло')  # type: ignore[arg-type]

    assert updated is not None
    assert updated.component_name == 'Новое масло'
    assert updated.replacement_date == replacement.replacement_date
    assert updated.km_at_replacement == replacement.km_at_replacement
    assert updated.component_price == replacement.component_price
    assert updated.work_price == replacement.work_price
    assert updated.next_change_date == replacement.next_change_date


def test_update_prices_only(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(db_session)
    service = _service(db_session)

    updated = _update(
        service,
        replacement.id,  # type: ignore[arg-type]
        component_price=7000,
        work_price=1500,
    )

    assert updated is not None
    assert updated.component_price == 7000
    assert updated.work_price == 1500
    assert updated.replacement_date == replacement.replacement_date
    assert updated.km_at_replacement == replacement.km_at_replacement


def test_update_date_recalculates_next_change_date_and_resets_flags(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(db_session)
    _set_date_flags(db_session, replacement.id)  # type: ignore[arg-type]
    service = _service(db_session)

    updated = _update(service, replacement.id, replacement_date=date(2026, 2, 1))  # type: ignore[arg-type]

    assert updated is not None
    assert updated.replacement_date == date(2026, 2, 1)
    assert updated.next_change_date == date(2027, 2, 1)
    assert _date_flags(db_session, replacement.id) == (False, False)  # type: ignore[arg-type]


def test_update_km_only(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(db_session)
    service = _service(db_session)

    updated = _update(service, replacement.id, km_at_replacement=13000)  # type: ignore[arg-type]

    assert updated is not None
    assert updated.km_at_replacement == 13000
    assert updated.replacement_date == replacement.replacement_date


def test_update_date_and_km_together(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    _add_replacement(
        db_session,
        replacement_date=date(2026, 1, 1),
        km=11000,
        next_change_date=date(2027, 1, 1),
    )
    replacement = _add_replacement(
        db_session,
        replacement_date=date(2026, 1, 10),
        km=12000,
        next_change_date=date(2027, 1, 10),
    )
    service = _service(db_session)

    updated = _update(
        service,
        replacement.id,  # type: ignore[arg-type]
        replacement_date=date(2026, 1, 5),
        km_at_replacement=11500,
    )

    assert updated is not None
    assert updated.replacement_date == date(2026, 1, 5)
    assert updated.km_at_replacement == 11500
    assert updated.next_change_date == date(2027, 1, 5)


def test_update_validates_final_km_and_date_pair(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    _add_replacement(
        db_session,
        replacement_date=date(2026, 1, 10),
        km=10000,
        next_change_date=date(2027, 1, 10),
    )
    _add_replacement(
        db_session,
        replacement_date=date(2026, 1, 21),
        km=11500,
        next_change_date=date(2027, 1, 21),
    )
    replacement = _add_replacement(
        db_session,
        replacement_date=date(2026, 1, 20),
        km=12000,
        next_change_date=date(2027, 1, 20),
    )
    service = _service(db_session)

    with pytest.raises(ValueError, match='позже следующей замены'):
        _update(
            service,
            replacement.id,  # type: ignore[arg-type]
            replacement_date=date(2026, 1, 25),
            km_at_replacement=11000,
        )


def test_update_vehicle_km_only_upward(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(db_session, km=9000)
    service = _service(db_session)

    _update(service, replacement.id, km_at_replacement=8000)  # type: ignore[arg-type]
    assert VehicleRepository(db_session).find_by_id(1).current_km == 10000  # type: ignore[union-attr]

    _update(service, replacement.id, km_at_replacement=14000)  # type: ignore[arg-type]
    assert VehicleRepository(db_session).find_by_id(1).current_km == 14000  # type: ignore[union-attr]


def test_update_parking_ignores_km_and_work_price(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(
        db_session,
        component_type=ComponentType.PARKING_MONTHLY,
        km=0,
        component_price=8000,
        work_price=None,  # type: ignore[arg-type]
        interval_km=0,
        interval_months=None,
        next_change_date=date(2026, 2, 15),
    )
    service = _service(db_session)

    updated = _update(
        service,
        replacement.id,  # type: ignore[arg-type]
        km_at_replacement=999,
        work_price=500,
        component_name='Новое место',
    )

    assert updated is not None
    assert updated.km_at_replacement == 0
    assert updated.work_price is None
    assert updated.component_name == 'Новое место'


def test_update_parking_resets_flags_when_next_date_changes(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(
        db_session,
        component_type=ComponentType.PARKING_MONTHLY,
        km=0,
        component_price=8000,
        work_price=None,  # type: ignore[arg-type]
        interval_km=0,
        interval_months=None,
        next_change_date=date(2026, 2, 15),
    )
    _set_date_flags(db_session, replacement.id)  # type: ignore[arg-type]
    service = _service(db_session)

    _update(service, replacement.id, next_change_date=date(2026, 3, 15))  # type: ignore[arg-type]

    assert _date_flags(db_session, replacement.id) == (False, False)  # type: ignore[arg-type]


def test_update_tire_keeps_manual_next_change_date(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    replacement = _add_replacement(
        db_session,
        component_type=ComponentType.TIRE_CHANGE,
        km=12000,
        component_price=0,
        work_price=0,
        interval_km=0,
        interval_months=None,
        next_change_date=date(2026, 12, 31),
    )
    service = _service(db_session)

    updated = _update(
        service,
        replacement.id,  # type: ignore[arg-type]
        replacement_date=date(2026, 2, 1),
        km_at_replacement=12500,
        next_change_date=date(2027, 1, 1),
    )

    assert updated is not None
    assert updated.replacement_date == date(2026, 2, 1)
    assert updated.km_at_replacement == 12500
    assert updated.next_change_date == date(2027, 1, 1)


def test_update_priced_replacement_conflicts_with_repair(
    db_session: Session, vehicle: VehicleDTO,
) -> None:
    RepairService(db_session).create(
        vehicle.id,  # type: ignore[arg-type]
        _repair_request(),
        vehicle,
    )
    placeholder = ReplacementRepository(db_session).find_by_vehicle_and_component(
        1, ComponentType.ENGINE_OIL,
    )[0]
    service = _service(db_session)

    with pytest.raises(ValueError, match='входит в ремонт'):
        _update(service, placeholder.id, component_price=1000)  # type: ignore[arg-type]


def _repair_request() -> RepairCreateRequest:
    return RepairCreateRequest(
        repair_date=date(2026, 1, 15),
        km_at_repair=12000,
        description='ТО',
        work_cost=1000,
        parts_cost=5000,
        component_types=[ComponentType.ENGINE_OIL],
    )
