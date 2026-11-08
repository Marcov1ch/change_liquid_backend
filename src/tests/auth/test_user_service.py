from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.schemas import UserCreate
from app.auth.user_service import (
    create_user,
    email_conflict_exists,
    normalize_email,
    normalize_identifier,
    registration_conflict_exists,
    user_to_response,
)
from app.db.models import Base, UserDB


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _add_user(
    session: Session,
    username: str = 'alice',
    email: str = 'alice@example.com',
) -> UserDB:
    user = UserDB(
        username=username,
        email=email,
        hashed_password='hash',
        email_verified=False,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_identifier_and_email_normalization() -> None:
    assert normalize_identifier('  Alice@Example.COM ') == 'alice@example.com'
    assert normalize_email('  Alice@Example.COM ') == 'alice@example.com'


def test_registration_conflict_by_username(db_session: Session) -> None:
    _add_user(db_session, username='alice')

    assert registration_conflict_exists(db_session, 'alice', 'other@example.com') is True


def test_registration_conflict_by_email_case_insensitive(db_session: Session) -> None:
    _add_user(db_session, email='alice@example.com')

    assert registration_conflict_exists(db_session, 'bob', 'ALICE@example.com') is True


def test_registration_conflict_cross_field(db_session: Session) -> None:
    _add_user(db_session, username='bob@example.com', email='bob@example.org')

    assert registration_conflict_exists(db_session, 'alice', 'bob@example.com') is True


def test_email_conflict_excludes_current_user(db_session: Session) -> None:
    user = _add_user(db_session)

    assert email_conflict_exists(db_session, 'alice@example.com', user.id) is False
    assert email_conflict_exists(db_session, 'alice@example.com') is True


def test_create_user_normalizes_email(db_session: Session) -> None:
    created = create_user(
        db_session,
        UserCreate(username='bob', email='Bob@Example.COM', password='secret'),
    )

    assert created.email == 'bob@example.com'
    assert created.hashed_password != 'secret'
    assert user_to_response(created).username == 'bob'
