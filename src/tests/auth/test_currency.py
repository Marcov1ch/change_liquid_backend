import asyncio
from typing import Iterator

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.routes.account import mark_profile_visited, update_currency
from app.auth.schemas import UpdateCurrencyRequest
from app.auth.user_service import create_user, user_to_response
from app.auth.schemas import UserCreate
from app.common.enums import Currency
from app.db.models import Base, UserDB


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _user(session: Session) -> UserDB:
    user = create_user(
        session,
        UserCreate(username='alice', email='alice@example.com', password='secret'),
    )
    return user


def test_new_user_has_rub_and_profile_not_visited(db_session: Session) -> None:
    response = user_to_response(_user(db_session))

    assert response.currency == 'RUB'
    assert response.profile_visited is False


def test_update_currency_without_records(db_session: Session) -> None:
    user = _user(db_session)

    response = update_currency(
        request=UpdateCurrencyRequest(currency=Currency.EUR),
        db=db_session,
        current_user=user,
    )

    assert response.user.currency == 'EUR'
    assert response.from_currency == 'RUB'
    assert response.to_currency == 'EUR'
    assert response.records_count == 0
    assert response.rate is None
    assert user.currency == 'EUR'


def test_update_currency_rejects_unknown_code() -> None:
    with pytest.raises(ValidationError):
        UpdateCurrencyRequest(currency='GBP')


def test_mark_profile_visited_is_idempotent(db_session: Session) -> None:
    user = _user(db_session)

    first = asyncio.run(mark_profile_visited(db=db_session, current_user=user))
    second = asyncio.run(mark_profile_visited(db=db_session, current_user=user))

    assert first.profile_visited is True
    assert second.profile_visited is True
    assert user.profile_visited is True
