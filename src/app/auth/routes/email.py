from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.email_tokens import queue_verification_email
from app.auth.jwt import get_current_user, verify_token
from app.auth.rate_limit import _check_resend_cooldown
from app.auth.schemas import (
    MessageResponse,
    VerifyEmailRequest,
)
from app.auth.user_service import find_user_by_id
from app.db.database import get_db
from app.db.models import UserDB

router = APIRouter()


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Подтвердить email по токену из письма."""
    try:
        payload = verify_token(request.token, "email_verification")
        user_id_raw = payload.get("sub")
        email = payload.get("email")
        if not user_id_raw or not email:
            raise ValueError("invalid payload")
        user_id = int(user_id_raw)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный или просроченный токен",
        )

    user = find_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не найден",
        )

    if user.email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка недействительна: email был изменён",
        )

    if not user.email_verified:
        user.email_verified = True
        db.commit()

    return MessageResponse(detail="Email подтверждён")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: UserDB = Depends(get_current_user),
) -> MessageResponse:
    """Повторно отправить письмо подтверждения email."""
    if current_user.email_verified:
        return MessageResponse(detail="Email уже подтверждён")

    _check_resend_cooldown(current_user.id)

    queue_verification_email(background_tasks, current_user)

    return MessageResponse(detail="Письмо с подтверждением отправлено")
