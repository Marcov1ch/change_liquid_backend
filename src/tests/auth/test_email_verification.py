import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Iterator
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.handler import (
    forgot_password,
    register,
    resend_cooldowns,
    resend_verification,
    update_email,
    verify_email,
)
from app.auth.jwt import (
    ALGORITHM,
    SECRET_KEY,
    create_email_verification_token,
)
from app.auth.schemas import (
    ForgotPasswordRequest,
    UpdateEmailRequest,
    UserCreate,
    VerifyEmailRequest,
)
from app.db.models import Base, UserDB
from app.services.notification_service import _PendingItem, _send_grouped


@pytest.fixture(autouse=True)
def clear_resend_cooldowns() -> Iterator[None]:
    resend_cooldowns.clear()
    yield
    resend_cooldowns.clear()


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
        email_verified=False,
        is_active=True,
        token_version=0,
    )
    db_session.add(db_user)
    db_session.commit()
    db_session.refresh(db_user)
    return db_user


class TestRegistration:
    def test_registration_creates_unverified_user_and_sends_email(
        self, db_session: Session,
    ) -> None:
        background_tasks = BackgroundTasks()

        asyncio.run(register(
            UserCreate(username="newuser", email="new@example.com", password="secret"),
            background_tasks=background_tasks,
            db=db_session,
        ))

        created = db_session.query(UserDB).filter(UserDB.username == "newuser").first()
        assert created is not None
        assert created.email_verified is False
        assert len(background_tasks.tasks) == 1

    def test_registration_starts_resend_cooldown(self, db_session: Session) -> None:
        asyncio.run(register(
            UserCreate(username="newuser", email="new@example.com", password="secret"),
            background_tasks=BackgroundTasks(),
            db=db_session,
        ))
        created = db_session.query(UserDB).filter(UserDB.username == "newuser").first()
        assert created is not None

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(resend_verification(
                background_tasks=BackgroundTasks(),
                current_user=created,
            ))

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers


class TestResendVerification:
    def test_first_resend_succeeds_and_starts_cooldown(self, user: UserDB) -> None:
        background_tasks = BackgroundTasks()

        response = asyncio.run(resend_verification(
            background_tasks=background_tasks,
            current_user=user,
        ))

        assert response.detail == "Письмо с подтверждением отправлено"
        assert len(background_tasks.tasks) == 1

    def test_second_resend_is_throttled(self, user: UserDB) -> None:
        asyncio.run(resend_verification(
            background_tasks=BackgroundTasks(),
            current_user=user,
        ))

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(resend_verification(
                background_tasks=BackgroundTasks(),
                current_user=user,
            ))

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers is not None
        retry_after = int(exc_info.value.headers["Retry-After"])
        assert 1 <= retry_after <= 60


class TestVerifyEmail:
    def test_verifies_user_email(self, user: UserDB, db_session: Session) -> None:
        token = create_email_verification_token(user.id, user.email)

        response = asyncio.run(verify_email(
            VerifyEmailRequest(token=token),
            db=db_session,
        ))

        db_session.refresh(user)
        assert response.detail == "Email подтверждён"
        assert user.email_verified is True

    def test_rejects_token_for_another_email(self, user: UserDB, db_session: Session) -> None:
        token = create_email_verification_token(user.id, "other@example.com")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(verify_email(VerifyEmailRequest(token=token), db=db_session))

        assert exc_info.value.status_code == 400

    def test_rejects_expired_token(self, user: UserDB, db_session: Session) -> None:
        token = jwt.encode(
            {
                "sub": str(user.id),
                "email": user.email,
                "type": "email_verification",
                "exp": datetime(2020, 1, 1, tzinfo=timezone.utc),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )

        with pytest.raises(HTTPException):
            asyncio.run(verify_email(VerifyEmailRequest(token=token), db=db_session))


class TestUpdateEmail:
    def test_changes_email_marks_unverified_and_keeps_session(
        self, user: UserDB, db_session: Session,
    ) -> None:
        background_tasks = BackgroundTasks()

        response = asyncio.run(update_email(
            UpdateEmailRequest(email="new@example.com"),
            background_tasks=background_tasks,
            db=db_session,
            current_user=user,
        ))

        db_session.refresh(user)
        assert user.email == "new@example.com"
        assert user.email_verified is False
        assert user.token_version == 0
        assert response.email_verified is False
        assert len(background_tasks.tasks) == 1

    def test_same_email_is_noop(self, user: UserDB, db_session: Session) -> None:
        background_tasks = BackgroundTasks()

        response = asyncio.run(update_email(
            UpdateEmailRequest(email=user.email),
            background_tasks=background_tasks,
            db=db_session,
            current_user=user,
        ))

        assert response.email_verified is False
        assert len(background_tasks.tasks) == 0

    def test_email_change_starts_resend_cooldown(
        self, user: UserDB, db_session: Session,
    ) -> None:
        asyncio.run(update_email(
            UpdateEmailRequest(email="new@example.com"),
            background_tasks=BackgroundTasks(),
            db=db_session,
            current_user=user,
        ))

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(resend_verification(
                background_tasks=BackgroundTasks(),
                current_user=user,
            ))

        assert exc_info.value.status_code == 429


class TestForgotPassword:
    def test_does_not_send_for_unverified_user(
        self, user: UserDB, db_session: Session,
    ) -> None:
        background_tasks = BackgroundTasks()

        asyncio.run(forgot_password(
            ForgotPasswordRequest(username=user.username, email=user.email),
            background_tasks=background_tasks,
            db=db_session,
        ))

        assert len(background_tasks.tasks) == 0

    def test_sends_for_verified_user(self, user: UserDB, db_session: Session) -> None:
        user.email_verified = True
        db_session.commit()
        background_tasks = BackgroundTasks()

        asyncio.run(forgot_password(
            ForgotPasswordRequest(username=user.username, email=user.email),
            background_tasks=background_tasks,
            db=db_session,
        ))

        assert len(background_tasks.tasks) == 1


class TestNotificationSuppression:
    def test_grouped_notification_skipped_for_unverified_email(self) -> None:
        repository = MagicMock()
        vehicle = {
            "id": 1,
            "brand": "Toyota",
            "model": "Camry",
            "plate_number": "A123AA178",
            "owner_email": "user@example.com",
            "owner_email_verified": False,
            "owner_username": "user",
        }
        pending = [
            _PendingItem(
                last={"id": 10},
                comp_key="engine_oil",
                km_remaining=-100,
                status="overdue",
                overdue_notified_at_km=20000,
            ),
        ]

        with patch(
            "app.services.notification_service.send_grouped_notification_email",
        ) as mock_send:
            _send_grouped(repository, vehicle, pending)

        mock_send.assert_not_called()
        repository.update_notify_tracking.assert_not_called()

    def test_date_notification_skipped_for_unverified_email(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from app.services import scheduler as scheduler_module

        vehicle = {
            "id": 1,
            "brand": "Toyota",
            "model": "Camry",
            "plate_number": "A123AA178",
            "interval_months": {},
            "notify_flags": {"tire_change": True},
            "owner_email": "user@example.com",
            "owner_email_verified": False,
            "owner_username": "user",
        }
        last_replacement = {
            "id": 10,
            "component_type": "tire_change",
            "component_name": "Tires",
            "replacement_date": date.today() - timedelta(days=365),
            "next_change_date": date.today() - timedelta(days=1),
            "date_warning_notified": False,
            "date_overdue_notified": False,
        }

        vehicle_repo = MagicMock()
        vehicle_repo.find_all_active_with_owner.return_value = [vehicle]
        replacement_repo = MagicMock()
        replacement_repo.get_last_replacement_with_notify.return_value = last_replacement

        monkeypatch.setattr(scheduler_module, "SessionLocal", lambda: MagicMock())
        monkeypatch.setattr(scheduler_module, "VehicleRepository", lambda db: vehicle_repo)
        monkeypatch.setattr(scheduler_module, "ReplacementRepository", lambda db: replacement_repo)
        monkeypatch.setattr(scheduler_module, "send_date_notification_email", MagicMock())

        scheduler_module._check_date_notifications()

        scheduler_module.send_date_notification_email.assert_not_called()
        replacement_repo.update_date_notify_tracking.assert_not_called()
