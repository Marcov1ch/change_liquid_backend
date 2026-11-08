import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import BackgroundTasks

from app.auth.jwt import (
    ALGORITHM,
    SECRET_KEY,
    create_email_verification_token,
)
from app.auth.rate_limit import _mark_verification_sent
from app.db.models import UserDB
from app.services.email_service import send_reset_password_email, send_verification_email

logger = logging.getLogger(__name__)


def _send_verification_email_safe(to_email: str, token: str) -> None:
    """Отправить письмо подтверждения email, не роняя фоновую задачу."""
    try:
        send_verification_email(to_email=to_email, token=token)
    except Exception:
        logger.exception('Failed to send verification email to %s', to_email)


def _send_reset_password_email_safe(to_email: str, token: str) -> None:
    """Отправить письмо восстановления пароля, не роняя фоновую задачу."""
    try:
        send_reset_password_email(to_email=to_email, token=token)
    except Exception:
        logger.exception('Failed to send reset-password email to %s', to_email)


def queue_verification_email(
    background_tasks: BackgroundTasks,
    user: UserDB,
) -> None:
    """Поставить в фон отправку письма подтверждения и запустить кулдаун."""
    token = create_email_verification_token(user.id, user.email)
    background_tasks.add_task(
        _send_verification_email_safe,
        to_email=user.email,
        token=token,
    )
    _mark_verification_sent(user.id)


def create_password_reset_token(user: UserDB) -> str:
    """Создать токен сброса пароля."""
    token: str = jwt.encode(
        {
            "sub": user.email,
            "type": "password_reset",
            "ver": user.token_version,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return token


def queue_password_reset_email(
    background_tasks: BackgroundTasks,
    user: UserDB,
) -> None:
    """Поставить в фон отправку письма сброса пароля."""
    background_tasks.add_task(
        _send_reset_password_email_safe,
        to_email=user.email,
        token=create_password_reset_token(user),
    )
