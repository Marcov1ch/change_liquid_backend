from datetime import date, timedelta
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.other_expense.schema import OtherExpenseCreateRequest
from app.db.models import Base
from app.services.other_expense_service import OtherExpenseService


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _request(
    name: str = 'Штраф',
    expense_date: date | None = None,
    amount: int = 500,
) -> OtherExpenseCreateRequest:
    return OtherExpenseCreateRequest.model_construct(
        name=name,
        expense_date=expense_date or date(2026, 1, 15),
        amount=amount,
    )


def test_create_normalizes_name(db_session: Session) -> None:
    service = OtherExpenseService(db_session)

    created = service.create(1, _request(name='  Мойка  '))

    assert created.id is not None
    assert created.name == 'Мойка'
    assert created.vehicle_id == 1
    assert created.amount == 500


def test_create_rejects_empty_name(db_session: Session) -> None:
    service = OtherExpenseService(db_session)

    with pytest.raises(ValueError, match='пустым'):
        service.create(1, _request(name='   '))


def test_create_rejects_long_name(db_session: Session) -> None:
    service = OtherExpenseService(db_session)

    with pytest.raises(ValueError, match='длиннее 100'):
        service.create(1, _request(name='x' * 101))


def test_create_rejects_non_positive_amount(db_session: Session) -> None:
    service = OtherExpenseService(db_session)

    with pytest.raises(ValueError, match='больше 0'):
        service.create(1, _request(amount=0))


def test_create_rejects_future_date(db_session: Session) -> None:
    service = OtherExpenseService(db_session)
    future = date.today() + timedelta(days=1)

    with pytest.raises(ValueError, match='позже сегодняшнего дня'):
        service.create(1, _request(expense_date=future))


def test_get_by_vehicle_sorts_by_date_and_id_desc(db_session: Session) -> None:
    service = OtherExpenseService(db_session)
    service.create(1, _request(name='Старая', expense_date=date(2026, 1, 1), amount=100))
    service.create(1, _request(name='Новая 1', expense_date=date(2026, 2, 1), amount=200))
    service.create(1, _request(name='Новая 2', expense_date=date(2026, 2, 1), amount=300))
    service.create(2, _request(name='Чужая', expense_date=date(2026, 3, 1), amount=400))

    expenses = service.get_by_vehicle(1)

    assert [expense.name for expense in expenses] == ['Новая 2', 'Новая 1', 'Старая']


def test_update_partial_fields(db_session: Session) -> None:
    service = OtherExpenseService(db_session)
    created = service.create(1, _request())

    updated = service.update(created.id, name='Парковка', amount=700)

    assert updated is not None
    assert updated.name == 'Парковка'
    assert updated.amount == 700
    assert updated.expense_date == created.expense_date


def test_update_missing_returns_none(db_session: Session) -> None:
    service = OtherExpenseService(db_session)

    assert service.update(999, amount=700) is None


def test_update_rejects_invalid_values(db_session: Session) -> None:
    service = OtherExpenseService(db_session)
    created = service.create(1, _request())

    with pytest.raises(ValueError, match='больше 0'):
        service.update(created.id, amount=0)
    with pytest.raises(ValueError, match='пустым'):
        service.update(created.id, name='  ')


def test_delete_and_delete_by_vehicle(db_session: Session) -> None:
    service = OtherExpenseService(db_session)
    first = service.create(1, _request(name='Первая'))
    service.create(1, _request(name='Вторая'))
    service.create(2, _request(name='Другая'))

    assert service.delete(first.id) is True
    assert service.delete(first.id) is False

    deleted = service.delete_by_vehicle(1)

    assert deleted == 1
    assert service.get_by_vehicle(1) == []
    assert len(service.get_by_vehicle(2)) == 1
