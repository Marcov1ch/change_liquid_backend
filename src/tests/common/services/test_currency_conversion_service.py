from datetime import date, datetime, timezone
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.common.enums import ComponentType, TireEventType
from app.db.models import (
    Base,
    BrandDB,
    FuelRecordDB,
    ModelDB,
    OtherExpenseDB,
    RepairDB,
    ReplacementDB,
    TireSetDB,
    UserDB,
    VehicleDB,
)
from app.services.currency_conversion_service import CurrencyConversionService
from app.services.currency_service import CurrencyRateService


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def user_with_money(db_session: Session) -> UserDB:
    brand = BrandDB(name='VW')
    model = ModelDB(name='Golf', brand=brand)
    user = UserDB(
        username='alice',
        email='alice@example.com',
        hashed_password='hash',
        currency='RUB',
        profile_visited=True,
    )
    db_session.add_all([brand, model, user])
    db_session.flush()

    vehicle = VehicleDB(
        brand_id=brand.id,
        model_id=model.id,
        plate_number='A123AA',
        year=2020,
        current_km=10000,
        is_active=False,
        owner_id=user.id,
    )
    db_session.add(vehicle)
    db_session.flush()

    tire_set = TireSetDB(
        vehicle_id=vehicle.id,
        name='Winter',
        season='winter',
        purchase_price=3000,
    )
    db_session.add(tire_set)
    db_session.flush()

    db_session.add_all([
        ReplacementDB(
            vehicle_id=vehicle.id,
            component_type=ComponentType.ENGINE_OIL.value,
            component_name='Oil',
            component_price=1000,
            work_price=100,
            replacement_date=date(2026, 1, 1),
            km_at_replacement=9000,
            interval_km=7000,
        ),
        ReplacementDB(
            vehicle_id=vehicle.id,
            component_type=ComponentType.TIRE_CHANGE.value,
            component_name='Winter',
            component_price=3000,
            replacement_date=date(2026, 1, 1),
            km_at_replacement=9000,
            interval_km=0,
            tire_set_id=tire_set.id,
            tire_event_type=TireEventType.PURCHASE.value,
        ),
        RepairDB(
            vehicle_id=vehicle.id,
            repair_date=date(2026, 1, 2),
            km_at_repair=9500,
            work_cost=500,
            parts_cost=250,
        ),
        FuelRecordDB(
            vehicle_id=vehicle.id,
            fuel_date=date(2026, 1, 3),
            km_at_fuel=9600,
            liters=30.0,
            total_cost=2000,
        ),
        OtherExpenseDB(
            vehicle_id=vehicle.id,
            name='Wash',
            expense_date=date(2026, 1, 4),
            amount=100,
        ),
    ])
    db_session.commit()
    db_session.refresh(user)
    return user


def _rates_service() -> CurrencyRateService:
    service = CurrencyRateService()
    service._rates = {'RUB': 1.0, 'USD': 100.0, 'BYN': 30.0, 'EUR': 120.0}
    service._fetched_at = datetime.now(timezone.utc)
    service._source = 'cbr'
    return service


def test_preview_counts_records_and_conversion_rate(
    db_session: Session,
    user_with_money: UserDB,
) -> None:
    service = CurrencyConversionService(db_session, _rates_service())

    preview = service.preview(user_with_money, 'USD')

    assert preview.from_currency == 'RUB'
    assert preview.to_currency == 'USD'
    assert preview.rate == pytest.approx(0.01)
    assert preview.to_rub_rate == 100.0
    assert preview.records_count == 6
    assert preview.vehicles_count == 1
    assert preview.stale is False


def test_apply_converts_all_money_fields(
    db_session: Session,
    user_with_money: UserDB,
) -> None:
    service = CurrencyConversionService(db_session, _rates_service())

    result = service.apply(user_with_money, 'USD')

    db_session.expire_all()
    user = db_session.query(UserDB).filter(UserDB.id == user_with_money.id).one()
    replacement = db_session.query(ReplacementDB).filter(
        ReplacementDB.component_type == ComponentType.ENGINE_OIL.value,
    ).one()
    purchase = db_session.query(ReplacementDB).filter(
        ReplacementDB.tire_event_type == TireEventType.PURCHASE.value,
    ).one()
    tire_set = db_session.query(TireSetDB).one()
    repair = db_session.query(RepairDB).one()
    fuel = db_session.query(FuelRecordDB).one()
    expense = db_session.query(OtherExpenseDB).one()

    assert result.records_count == 6
    assert result.rate == pytest.approx(0.01)
    assert user.currency == 'USD'
    assert float(replacement.component_price) == 10.0
    assert float(replacement.work_price) == 1.0
    assert float(purchase.component_price) == 30.0
    assert float(tire_set.purchase_price) == 30.0
    assert float(repair.work_cost) == 5.0
    assert float(repair.parts_cost) == 2.5
    assert float(fuel.total_cost) == 20.0
    assert float(expense.amount) == 1.0


def test_apply_same_currency_does_not_fetch_rates(
    db_session: Session,
    user_with_money: UserDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CurrencyConversionService(db_session, _rates_service())
    monkeypatch.setattr(
        service.rates,
        '_fetch_rates',
        lambda: (_ for _ in ()).throw(RuntimeError('no network')),
    )

    result = service.apply(user_with_money, 'RUB')

    assert result.rate == 1.0
    assert result.records_count == 6
    assert user_with_money.currency == 'RUB'


def test_apply_without_records_does_not_fetch_rates(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = UserDB(
        username='empty',
        email='empty@example.com',
        hashed_password='hash',
        currency='RUB',
    )
    db_session.add(user)
    db_session.commit()

    service = CurrencyConversionService(db_session, _rates_service())
    monkeypatch.setattr(
        service.rates,
        '_fetch_rates',
        lambda: (_ for _ in ()).throw(RuntimeError('no network')),
    )

    result = service.apply(user, 'EUR')

    assert result.rate is None
    assert result.records_count == 0
    assert user.currency == 'EUR'
