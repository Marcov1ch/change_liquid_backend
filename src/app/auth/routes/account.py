from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.email_tokens import queue_verification_email
from app.auth.jwt import get_current_user
from app.auth.password import hash_password, verify_password
from app.auth.schemas import (
    ChangePasswordRequest,
    MessageResponse,
    UpdateEmailRequest,
    UserResponse,
)
from app.auth.user_service import (
    email_conflict_exists,
    normalize_email,
    user_to_response,
)
from app.db.database import get_db
from app.db.models import UserDB

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserDB = Depends(get_current_user)) -> UserResponse:
    """Получить информацию о текущем пользователе."""
    return user_to_response(current_user)


@router.patch("/email", response_model=UserResponse)
async def update_email(
    request: UpdateEmailRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> UserResponse:
    """Сменить email текущего пользователя."""
    new_email = normalize_email(str(request.email))
    if new_email == normalize_email(current_user.email):
        return user_to_response(current_user)

    if email_conflict_exists(db, new_email, exclude_user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже используется"
        )

    current_user.email = new_email
    current_user.email_verified = False
    db.commit()
    db.refresh(current_user)

    queue_verification_email(background_tasks, current_user)

    return user_to_response(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> MessageResponse:
    """Сменить пароль текущего пользователя."""
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный пароль"
        )

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль должен отличаться от старого"
        )

    current_user.hashed_password = hash_password(request.new_password)
    current_user.token_version += 1
    db.commit()

    return MessageResponse(detail="Пароль успешно изменён")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> MessageResponse:
    """Деактивировать аккаунт (soft delete)."""
    current_user.is_active = False
    current_user.token_version += 1
    db.commit()

    return MessageResponse(detail="Аккаунт деактивирован")
