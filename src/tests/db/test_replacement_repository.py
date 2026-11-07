from datetime import date
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common.enums import ComponentType
from app.db.models import Base, ReplacementDB
from app.repository.replacement_repository import ReplacementRepository


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _add_replacement(
    session: Session,
    component_type: ComponentType,
    replacement_date: date,
    km: int = 0,
    next_change_date: date | None = None,
) -> ReplacementDB:
    db_replacement = ReplacementDB(
        vehicle_id=1,
        component_type=component_type.value,
        component_name='Тест',
        replacement_date=replacement_date,
        km_at_replacement=km,
        interval_km=0,
        next_change_date=next_change_date,
    )
    session.add(db_replacement)
    session.commit()
    session.refresh(db_replacement)
    return db_replacement


def _seed_backfilled_parking_and_oil(
    session: Session,
) -> tuple[ReplacementDB, ReplacementDB, ReplacementDB, ReplacementDB]:
    parking_new = _add_replacement(
        session, ComponentType.PARKING_MONTHLY, date(2026, 2, 1), next_change_date=date(2026, 3, 1),
    )
    parking_old = _add_replacement(
        session, ComponentType.PARKING_MONTHLY, date(2026, 1, 1), next_change_date=date(2026, 2, 1),
    )
    oil_low = _add_replacement(session, ComponentType.ENGINE_OIL, date(2026, 2, 1), km=1000)
    oil_high = _add_replacement(session, ComponentType.ENGINE_OIL, date(2026, 1, 1), km=2000)
    return parking_new, parking_old, oil_low, oil_high


def test_latest_ids_prefer_date_for_parking_and_km_for_regular(db_session: Session) -> None:
    parking_new, parking_old, _oil_low, oil_high = _seed_backfilled_parking_and_oil(db_session)

    latest_ids = ReplacementRepository(db_session).get_latest_replacement_ids(vehicle_id=1)

    assert latest_ids == {parking_new.id, oil_high.id}
    assert parking_old.id not in latest_ids


def test_last_replacement_prefers_date_for_parking(db_session: Session) -> None:
    parking_new, _parking_old, _oil_low, _oil_high = _seed_backfilled_parking_and_oil(db_session)

    last = ReplacementRepository(db_session).get_last_replacement(1, ComponentType.PARKING_MONTHLY)

    assert last is not None
    assert last.id == parking_new.id


def test_last_replacement_with_notify_prefers_date_for_parking(db_session: Session) -> None:
    parking_new, _parking_old, _oil_low, _oil_high = _seed_backfilled_parking_and_oil(db_session)

    last = ReplacementRepository(db_session).get_last_replacement_with_notify(
        1, ComponentType.PARKING_MONTHLY,
    )

    assert last is not None
    assert last["id"] == parking_new.id


def test_last_replacements_with_notify_uses_date_for_parking_and_km_for_regular(
    db_session: Session,
) -> None:
    parking_new, _parking_old, _oil_low, oil_high = _seed_backfilled_parking_and_oil(db_session)

    lasts = ReplacementRepository(db_session).get_last_replacements_with_notify(1)
    by_type = {last["component_type"]: last for last in lasts}

    assert by_type[ComponentType.PARKING_MONTHLY.value]["id"] == parking_new.id
    assert by_type[ComponentType.ENGINE_OIL.value]["id"] == oil_high.id
