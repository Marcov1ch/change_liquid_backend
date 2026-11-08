from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.email_tokens import queue_verification_email
from app.auth.schemas import UserCreate, UserResponse
from app.auth.user_service import (
    create_user,
    normalize_email,
    registration_conflict_exists,
    user_to_response,
)
from app.db.database import get_db

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Регистрация нового пользователя."""
    email = normalize_email(str(user_data.email))
    if registration_conflict_exists(db, user_data.username, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя пользователя или email уже заняты"
        )

    new_user = create_user(db, user_data)
    queue_verification_email(background_tasks, new_user)

    return user_to_response(new_user)
