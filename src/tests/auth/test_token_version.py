from typing import Iterator

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.jwt import (
    SECRET_KEY,
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    get_current_user,
    refresh_access_token,
)
from app.db.models import Base, UserDB


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def user(db_session: Session) -> UserDB:
    db_user = UserDB(
        username="testuser",
        email="test@example.com",
        hashed_password="not-a-real-hash",
        is_active=True,
    )
    db_session.add(db_user)
    db_session.commit()
    return db_user


def _decode(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


class TestTokenPayload:

    def test_tokens_contain_version(self) -> None:
        access = create_access_token(data={"sub": "u"}, version=5)
        refresh = create_refresh_token(data={"sub": "u"}, version=5)
        assert _decode(access)["ver"] == 5
        assert _decode(refresh)["ver"] == 5

    def test_old_token_without_version_rejected(self, user: UserDB, db_session: Session) -> None:
        token = jwt.encode(
            {"sub": user.username, "type": "access"},
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 401


class TestGetCurrentUser:

    def test_valid_version_passes(self, user: UserDB, db_session: Session) -> None:
        token = create_access_token(data={"sub": user.username}, version=user.token_version)
        assert get_current_user(token=token, db=db_session) is user

    def test_stale_version_rejected(self, user: UserDB, db_session: Session) -> None:
        token = create_access_token(data={"sub": user.username}, version=user.token_version)
        assert get_current_user(token=token, db=db_session) is user

        user.token_version += 1
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 401


class TestRefreshAccessToken:

    def test_valid_refresh_passes(self, user: UserDB, db_session: Session) -> None:
        refresh = create_refresh_token(data={"sub": user.username}, version=user.token_version)
        tokens = refresh_access_token(db_session, refresh)
        assert _decode(tokens["access_token"])["ver"] == user.token_version
        assert _decode(tokens["refresh_token"])["ver"] == user.token_version

    def test_stale_refresh_rejected(self, user: UserDB, db_session: Session) -> None:
        refresh = create_refresh_token(data={"sub": user.username}, version=user.token_version)

        user.token_version += 1
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            refresh_access_token(db_session, refresh)
        assert exc_info.value.status_code == 401
