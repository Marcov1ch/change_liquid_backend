from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.db.models import UserDB
from app.auth.password import hash_password, verify_password
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    get_current_user,
)
from app.auth.schemas import (
    RefreshRequest,
    UserCreate,
    UserResponse,
    Token,
    RefreshTokenResponse,
    UpdateEmailRequest,
    ChangePasswordRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

failed_attempts: defaultdict[str, list[datetime]] = defaultdict(list)


def check_rate_limit(username: str) -> bool:
    """Проверяет, не превышен ли лимит попыток входа (3 попытки за 5 минут)."""
    now = datetime.now()
    failed_attempts[username] = [
        t for t in failed_attempts[username]
        if now - t < timedelta(minutes=5)
    ]

    if len(failed_attempts[username]) >= 3:
        return False

    return True


def add_failed_attempt(username: str) -> None:
    """Добавляет неудачную попытку входа."""
    failed_attempts[username].append(datetime.now())


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Регистрация нового пользователя."""
    existing = db.query(UserDB).filter(
        (UserDB.username == user_data.username) | (UserDB.email == user_data.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    hashed = hash_password(user_data.password)
    new_user = UserDB(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Token:
    """Логин пользователя, возвращает JWT токен."""
    username = form_data.username

    if not check_rate_limit(username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later."
        )

    user = db.query(UserDB).filter(UserDB.username == username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        add_failed_attempt(username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not user.is_active:
        add_failed_attempt(username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive"
        )

    failed_attempts[username].clear()

    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh(request: RefreshRequest) -> RefreshTokenResponse:
    """Обновить access и refresh токены (сброс срока до 14 дней)."""
    try:
        tokens = refresh_access_token(request.refresh_token)
        return RefreshTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh token: {err}",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserDB = Depends(get_current_user)) -> UserResponse:
    """Получить информацию о текущем пользователе."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.patch("/email", response_model=UserResponse)
async def update_email(
    request: UpdateEmailRequest,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> UserResponse:
    """Сменить email текущего пользователя."""
    existing = db.query(UserDB).filter(
        UserDB.email == request.email,
        UserDB.id != current_user.id,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use"
        )

    current_user.email = request.email
    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


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
            detail="Incorrect password"
        )

    if request.old_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the old one"
        )

    current_user.hashed_password = hash_password(request.new_password)
    db.commit()

    return MessageResponse(detail="Password changed successfully")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
) -> MessageResponse:
    """Деактивировать аккаунт (soft delete)."""
    current_user.is_active = False
    db.commit()

    return MessageResponse(detail="Account deactivated")
