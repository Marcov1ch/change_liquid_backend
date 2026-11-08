from datetime import date, timedelta
from typing import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.repair.schema import RepairCreateRequest
from app.api.replacement.schema import ReplacementCreateRequest, UpdateReplacementRequest
from app.common.enums import ComponentType
from app.db.models import Base, BrandDB, ModelDB, VehicleDB
from app.repository.replacement_repository import ReplacementRepository
from app.repository.vehicle_repository import VehicleRepository
from app.services.dto import ReplacementDTO, VehicleDTO
from app.services.repair_service import RepairService
from app.services.replacement_service import REPAIR_PLACEHOLDER_NAME, ReplacementService


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


def _request(
    repair_date: date = date(2026, 5, 10),
    km_at_repair: int = 12000,
    description: str | None = 'Плановое ТО',
    work_cost: int = 5000,
    parts_cost: int = 10000,
    component_types: list[ComponentType] | None = None,
) -> RepairCreateRequest:
    return RepairCreateRequest.model_construct(
        repair_date=repair_date,
        km_at_repair=km_at_repair,
        description=description,
        work_cost=work_cost,
        parts_cost=parts_cost,
        component_types=(
            component_types
            if component_types is not None
            else [ComponentType.ENGINE_OIL]
        ),
    )


def _linked(session: Session, repair_id: int | None) -> list[ReplacementDTO]:
    return ReplacementRepository(session).find_by_source_repair_id(repair_id or 0)


def _replacement(
    component_type: ComponentType,
    replacement_date: date,
    km: int,
    component_price: int = 0,
    work_price: int = 0,
) -> ReplacementDTO:
    return ReplacementDTO(
        id=None,
        vehicle_id=1,
        component_type=component_type,
        component_name='Тестовая замена',
        component_price=component_price,
        work_price=work_price,
        replacement_date=replacement_date,
        km_at_replacement=km,
        interval_km=7000,
    )


class TestRepairCreate:

    def test_creates_placeholders_for_selected_components(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)

        repair = service.create(
            vehicle.id,
            _request(component_types=[ComponentType.ENGINE_OIL, ComponentType.BRAKE_FLUID]),
            vehicle,
        )

        assert repair.id is not None
        replacements = ReplacementRepository(db_session).find_by_source_repair_id(repair.id)
        assert {item.component_type for item in replacements} == {
            ComponentType.ENGINE_OIL,
            ComponentType.BRAKE_FLUID,
        }
        for item in replacements:
            assert item.component_name == REPAIR_PLACEHOLDER_NAME
            assert item.component_price == 0
            assert item.work_price == 0
            assert item.replacement_date == date(2026, 5, 10)
            assert item.km_at_replacement == 12000

    def test_raises_vehicle_km_only_upward(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)

        service.create(vehicle.id, _request(km_at_repair=9000), vehicle)
        assert VehicleRepository(db_session).find_by_id(1).current_km == 10000  # type: ignore[union-attr]

        service.create(vehicle.id, _request(km_at_repair=15000), vehicle)
        assert VehicleRepository(db_session).find_by_id(1).current_km == 15000  # type: ignore[union-attr]

    def test_rejects_future_date(self, db_session: Session, vehicle: VehicleDTO) -> None:
        service = RepairService(db_session)

        with pytest.raises(ValueError, match='позже сегодняшнего'):
            service.create(
                vehicle.id,
                _request(repair_date=date.today() + timedelta(days=1)),
                vehicle,
            )

    def test_rejects_negative_km(self, db_session: Session, vehicle: VehicleDTO) -> None:
        service = RepairService(db_session)

        with pytest.raises(ValueError, match='отрицательным'):
            service.create(vehicle.id, _request(km_at_repair=-1), vehicle)

    def test_rejects_negative_cost(self, db_session: Session, vehicle: VehicleDTO) -> None:
        service = RepairService(db_session)

        with pytest.raises(ValueError, match='отрицательной'):
            service.create(vehicle.id, _request(work_cost=-1), vehicle)

    def test_rejects_date_based_component(self, db_session: Session, vehicle: VehicleDTO) -> None:
        service = RepairService(db_session)

        with pytest.raises(ValueError, match='нельзя добавить'):
            service.create(
                vehicle.id,
                _request(component_types=[ComponentType.INSURANCE]),
                vehicle,
            )

    def test_schema_rejects_date_based_component(self) -> None:
        with pytest.raises(ValidationError):
            RepairCreateRequest(
                repair_date=date(2026, 5, 10),
                km_at_repair=1000,
                component_types=[ComponentType.TIRE_CHANGE],
            )

    def test_rejects_priced_replacement_on_same_date(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        ReplacementRepository(db_session).save(
            _replacement(ComponentType.ENGINE_OIL, date(2026, 5, 10), 11000, 1000)
        )
        service = RepairService(db_session)

        with pytest.raises(ValueError, match='замена с ценой'):
            service.create(vehicle.id, _request(), vehicle)

    def test_allows_zero_cost_replacement_on_same_date(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        ReplacementRepository(db_session).save(
            _replacement(ComponentType.ENGINE_OIL, date(2026, 5, 10), 11000)
        )
        service = RepairService(db_session)

        repair = service.create(vehicle.id, _request(), vehicle)

        assert _linked(db_session, repair.id) == []


class TestRepairUpdate:

    def test_removes_untouched_placeholder_for_removed_component(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)
        repair = service.create(
            vehicle.id,
            _request(component_types=[ComponentType.ENGINE_OIL, ComponentType.BRAKE_FLUID]),
            vehicle,
        )

        service.update(
            repair.id,  # type: ignore[arg-type]
            _request(component_types=[ComponentType.ENGINE_OIL]),
        )

        replacements = _linked(db_session, repair.id)
        assert [item.component_type for item in replacements] == [ComponentType.ENGINE_OIL]

    def test_adds_placeholder_for_new_component(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)
        repair = service.create(vehicle.id, _request(), vehicle)

        service.update(
            repair.id,  # type: ignore[arg-type]
            _request(component_types=[ComponentType.ENGINE_OIL, ComponentType.COOLANT]),
        )

        replacements = _linked(db_session, repair.id)
        assert {item.component_type for item in replacements} == {
            ComponentType.ENGINE_OIL,
            ComponentType.COOLANT,
        }

    def test_moves_untouched_placeholder_when_date_changes(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)
        repair = service.create(vehicle.id, _request(), vehicle)

        service.update(
            repair.id,  # type: ignore[arg-type]
            _request(repair_date=date(2026, 5, 11)),
        )

        replacements = _linked(db_session, repair.id)
        assert len(replacements) == 1
        assert replacements[0].replacement_date == date(2026, 5, 11)

    def test_keeps_touched_placeholder_when_date_changes(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)
        repair = service.create(vehicle.id, _request(), vehicle)
        linked = _linked(db_session, repair.id)
        linked[0].component_name = 'Моё масло'
        ReplacementRepository(db_session).save(linked[0])
        old_id = linked[0].id

        service.update(
            repair.id,  # type: ignore[arg-type]
            _request(repair_date=date(2026, 5, 11)),
        )

        replacements = _linked(db_session, repair.id)
        assert len(replacements) == 1
        assert replacements[0].id == old_id
        assert replacements[0].replacement_date == date(2026, 5, 10)

    def test_does_not_recreate_manually_deleted_placeholder(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)
        repair = service.create(vehicle.id, _request(), vehicle)
        linked = _linked(db_session, repair.id)
        ReplacementRepository(db_session).delete(linked[0].id)  # type: ignore[arg-type]

        service.update(
            repair.id,  # type: ignore[arg-type]
            _request(repair_date=date(2026, 5, 11)),
        )

        assert _linked(db_session, repair.id) == []

    def test_detaches_touched_placeholder_on_component_removal(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)
        repair = service.create(vehicle.id, _request(), vehicle)
        linked = _linked(db_session, repair.id)
        linked[0].component_name = 'Моё масло'
        ReplacementRepository(db_session).save(linked[0])

        service.update(
            repair.id,  # type: ignore[arg-type]
            _request(component_types=[]),
        )

        kept = ReplacementRepository(db_session).find_by_id(linked[0].id)  # type: ignore[arg-type]
        assert kept is not None
        assert kept.source_repair_id is None


class TestRepairDelete:

    def test_deletes_untouched_and_detaches_touched(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        service = RepairService(db_session)
        repair = service.create(
            vehicle.id,
            _request(component_types=[ComponentType.ENGINE_OIL, ComponentType.BRAKE_FLUID]),
            vehicle,
        )
        linked = _linked(db_session, repair.id)
        touched = next(item for item in linked if item.component_type == ComponentType.ENGINE_OIL)
        touched.component_name = 'Моё масло'
        ReplacementRepository(db_session).save(touched)

        assert service.delete(repair.id) is True  # type: ignore[arg-type]

        remaining = ReplacementRepository(db_session).find_by_vehicle_id(1)
        assert [item.id for item in remaining] == [touched.id]
        assert remaining[0].source_repair_id is None


class TestReplacementConflict:

    def test_priced_replacement_rejected_for_repair_component(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        repair_service = RepairService(db_session)
        repair_service.create(vehicle.id, _request(), vehicle)

        service = ReplacementService(db_session)

        with pytest.raises(ValueError, match='входит в ремонт'):
            service.create(
                vehicle.id,
                ReplacementCreateRequest(
                    component_type=ComponentType.ENGINE_OIL,
                    component_name='Платная замена',
                    component_price=1000,
                    work_price=0,
                    replacement_date=date(2026, 5, 10),
                    km_at_replacement=12000,
                ),
                vehicle,
            )

    def test_zero_cost_replacement_allowed_for_repair_component(
        self, db_session: Session, vehicle: VehicleDTO,
    ) -> None:
        repair_service = RepairService(db_session)
        repair = repair_service.create(vehicle.id, _request(), vehicle)
        linked = _linked(db_session, repair.id)

        service = ReplacementService(db_session)
        updated = service.update(
            linked[0].id,  # type: ignore[arg-type]
            UpdateReplacementRequest(component_price=0),
        )

        assert updated is not None
        assert updated.component_price == 0
