import asyncio
from typing import Iterator

import pytest
from fastapi import BackgroundTasks, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request

from app.auth.jwt import verify_token
from app.auth.password import hash_password
from app.auth.rate_limit import failed_attempts
from app.auth.routes.registration import register
from app.auth.routes.session import login
from app.auth.schemas import ForgotPasswordRequest, UpdateEmailRequest, UserCreate
from app.auth.user_service import find_user_by_identifier, normalize_identifier
from app.db.models import Base, UserDB


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _reset_rate_limit_store() -> None:
    failed_attempts.clear()


def _add_user(
    session: Session,
    username: str,
    email: str,
    password: str = 'secret',
    email_verified: bool = False,
) -> UserDB:
    user = UserDB(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        email_verified=email_verified,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _request(ip: str = '9.9.9.9') -> Request:
    scope = {
        "type": "http",
        "headers": [],
        "client": (ip, 1234),
    }
    return Request(scope)


def _form(identifier: str, password: str = 'secret') -> OAuth2PasswordRequestForm:
    return OAuth2PasswordRequestForm(
        grant_type='password',
        username=identifier,
        password=password,
    )


class TestFindUserByIdentifier:

    def test_finds_by_username(self, db_session: Session) -> None:
        user = _add_user(db_session, 'alice', 'alice@example.com')

        assert find_user_by_identifier(db_session, 'alice') is not None
        assert find_user_by_identifier(db_session, 'alice').id == user.id  # type: ignore[union-attr]

    def test_finds_by_email(self, db_session: Session) -> None:
        user = _add_user(db_session, 'alice', 'alice@example.com')

        found = find_user_by_identifier(db_session, 'alice@example.com')

        assert found is not None
        assert found.id == user.id

    def test_finds_by_email_case_insensitive(self, db_session: Session) -> None:
        user = _add_user(db_session, 'alice', 'alice@example.com')

        found = find_user_by_identifier(db_session, 'ALICE@EXAMPLE.COM')

        assert found is not None
        assert found.id == user.id

    def test_finds_by_email_with_spaces(self, db_session: Session) -> None:
        user = _add_user(db_session, 'alice', 'alice@example.com')

        found = find_user_by_identifier(db_session, '  alice@example.com  ')

        assert found is not None
        assert found.id == user.id

    def test_username_has_priority(self, db_session: Session) -> None:
        by_username = _add_user(db_session, 'same@example.com', 'first@example.com')
        _add_user(db_session, 'second', 'same@example.com')

        found = find_user_by_identifier(db_session, 'same@example.com')

        assert found is not None
        assert found.id == by_username.id

    def test_returns_none_for_unknown_identifier(self, db_session: Session) -> None:
        assert find_user_by_identifier(db_session, 'nobody') is None


class TestLoginByIdentifier:

    def test_login_by_username(self, db_session: Session) -> None:
        user = _add_user(db_session, 'alice', 'alice@example.com')

        tokens = asyncio.run(
            login(request=_request(), form_data=_form('alice'), db=db_session)
        )

        payload = verify_token(tokens.access_token, 'access')
        assert payload['sub'] == user.username

    def test_login_by_email(self, db_session: Session) -> None:
        user = _add_user(db_session, 'alice', 'alice@example.com')

        tokens = asyncio.run(
            login(request=_request(), form_data=_form('ALICE@EXAMPLE.COM'), db=db_session)
        )

        payload = verify_token(tokens.access_token, 'access')
        assert payload['sub'] == user.username

    def test_login_by_unverified_email(self, db_session: Session) -> None:
        _add_user(db_session, 'alice', 'alice@example.com', email_verified=False)

        tokens = asyncio.run(
            login(request=_request(), form_data=_form('alice@example.com'), db=db_session)
        )

        assert tokens.access_token

    def test_login_with_old_email_fails_after_change(self, db_session: Session) -> None:
        user = _add_user(db_session, 'alice', 'alice@example.com')
        user.email = 'new@example.com'
        db_session.commit()

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                login(request=_request(), form_data=_form('alice@example.com'), db=db_session)
            )

        assert exc.value.status_code == 401

    def test_rate_limit_key_is_case_insensitive(self) -> None:
        assert normalize_identifier('  Alice@Example.COM ') == 'alice@example.com'


class TestEmailNormalization:

    def test_user_create_normalizes_email(self) -> None:
        user = UserCreate(username='alice', email='  Alice@Example.COM  ', password='secret')
        assert user.email == 'alice@example.com'

    def test_update_email_normalizes_email(self) -> None:
        request = UpdateEmailRequest(email='  Alice@Example.COM  ')
        assert request.email == 'alice@example.com'

    def test_forgot_password_normalizes_email(self) -> None:
        request = ForgotPasswordRequest(username='alice', email='  Alice@Example.COM  ')
        assert request.email == 'alice@example.com'

    def test_register_stores_normalized_email(self, db_session: Session) -> None:
        response = asyncio.run(
            register(
                user_data=UserCreate(
                    username='alice',
                    email='Alice@Example.COM',
                    password='secret',
                ),
                background_tasks=BackgroundTasks(),
                db=db_session,
            )
        )

        assert response.email == 'alice@example.com'

    def test_register_rejects_case_insensitive_email_duplicate(self, db_session: Session) -> None:
        _add_user(db_session, 'alice', 'alice@example.com')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                register(
                    user_data=UserCreate(
                        username='bob',
                        email='ALICE@example.com',
                        password='secret',
                    ),
                    background_tasks=BackgroundTasks(),
                    db=db_session,
                )
            )

        assert exc.value.status_code == 400

    def test_register_rejects_email_matching_existing_username(self, db_session: Session) -> None:
        _add_user(db_session, 'bob@example.com', 'bob@example.org')

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                register(
                    user_data=UserCreate(
                        username='alice',
                        email='BOB@example.com',
                        password='secret',
                    ),
                    background_tasks=BackgroundTasks(),
                    db=db_session,
                )
            )

        assert exc.value.status_code == 400
