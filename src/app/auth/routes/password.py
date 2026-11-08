from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.email_tokens import queue_password_reset_email
from app.auth.jwt import verify_token
from app.auth.password import hash_password
from app.auth.schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
)
from app.auth.user_service import normalize_email
from app.db.database import get_db
from app.db.models import UserDB

router = APIRouter()


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Отправить письмо для восстановления пароля."""
    user = db.query(UserDB).filter(
        UserDB.username == request.username,
        func.lower(UserDB.email) == normalize_email(str(request.email)),
    ).first()

    if not user or not user.email_verified:
        return MessageResponse(
            detail="Если такой email зарегистрирован, письмо отправлено"
        )

    queue_password_reset_email(background_tasks, user)

    return MessageResponse(
        detail="Если такой email зарегистрирован, письмо отправлено"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Сбросить пароль по токену."""
    try:
        payload = verify_token(request.token, "password_reset")
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недействительный токен",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный или просроченный токен",
        )

    user = db.query(UserDB).filter(
        func.lower(UserDB.email) == normalize_email(str(email))
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь не найден",
        )

    if payload.get("ver") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный или просроченный токен",
        )

    user.hashed_password = hash_password(request.new_password)
    user.token_version += 1
    db.commit()

    return MessageResponse(detail="Пароль успешно изменён")
